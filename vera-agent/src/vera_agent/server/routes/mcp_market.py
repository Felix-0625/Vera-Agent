"""MCP Registry helpers: look a server up in the Official Registry and turn it into a config entry.

Used by `mcp.py`. An npm package is installed with `--ignore-scripts` into its own folder and its `bin` entry
point is checked to stay inside that folder; a remote server must be a credential-free HTTPS endpoint. Nothing
here reads the request or writes the saved server list except `save_new_server`.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from vera_agent.server.state import ServerState

DEFAULT_MCP_CONFIG = {"servers": []}


class McpInstallError(Exception):
    """A rejected market install; the route returns ``{"error": message}`` with this status."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


_PACKAGE_NAME = re.compile(r"(?:@[a-zA-Z0-9._-]+/)?[a-zA-Z0-9._-]+")
_PACKAGE_VERSION = re.compile(r"[a-zA-Z0-9.+_-]+")


def fetch_registry_server(registry_id: str) -> dict | None:
    """The Official Registry record whose name is exactly ``registry_id``, or None."""
    url = "https://registry.modelcontextprotocol.io/v0.1/servers?" + urlencode(
        {"q": registry_id, "limit": 50, "version": "latest"}
    )
    req = UrlRequest(url, headers={"Accept": "application/json", "User-Agent": "VeraAgent/1.0"})
    with urlopen(req, timeout=15) as response:
        records = json.loads(response.read(2_000_000)).get("servers", [])
    for record in records:
        server = record.get("server", record)
        if server.get("name") == registry_id:
            return server
    return None


def _repository_url(server: dict) -> str:
    repository = server.get("repository") or {}
    return repository.get("url", "") if isinstance(repository, dict) else str(repository)


def remote_entry(server: dict, registry_id: str, target_id: str) -> dict:
    """Config entry for a credential-free HTTPS Streamable HTTP endpoint; anything else is refused."""
    remote = next(
        (
            item
            for item in server.get("remotes", [])
            if isinstance(item, dict) and item.get("type") == "streamable-http"
        ),
        None,
    )
    remote_url = str(remote.get("url") or "") if remote else ""
    parsed_url = urlsplit(remote_url)
    if (
        not remote
        or parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        raise McpInstallError("This MCP server has no supported, credential-free HTTPS Streamable HTTP endpoint.")
    return {
        "id": target_id,
        "registry_id": registry_id,
        "name": server.get("title") or server.get("name") or registry_id,
        "type": "remote",
        "transport": "streamable-http",
        "url": remote_url,
        "status": "stopped",
        "enabled": False,
        "command": "",
        "args": [],
        "env": {},
        "headers": {},
        "tools": [],
        "repository": _repository_url(server),
        "registry_version": server.get("version", ""),
    }


def _npm_install_command(package_name: str, version: str, target_dir: Path) -> tuple[str, list[str]]:
    """The program and arguments that install one pinned package without running its scripts."""
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is not installed or is not available on PATH.")
    args = [
        npm,
        "install",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--registry=https://registry.npmjs.org",
        "--prefix",
        str(target_dir),
        f"{package_name}@{version}",
    ]
    if os.name == "nt" and npm.lower().endswith((".cmd", ".bat")):
        return os.environ.get("COMSPEC", "cmd.exe"), ["/d", "/s", "/c", subprocess.list2cmdline(args)]
    return args[0], args[1:]


def _package_entrypoint(package_dir: Path) -> Path:
    """The installed package's first ``bin`` script, which must exist inside the package directory."""
    manifest = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
    binaries = manifest.get("bin")
    if isinstance(binaries, str):
        entrypoint = binaries
    elif isinstance(binaries, dict) and binaries:
        entrypoint = next(iter(binaries.values()))
    else:
        raise RuntimeError("Installed npm package does not expose a command-line entry point.")
    executable = (package_dir / entrypoint).resolve()
    if package_dir.resolve() not in executable.parents or not executable.is_file():
        raise RuntimeError("The npm package entry point is missing or escapes its package directory.")
    return executable


async def npm_entry(server: dict, package: dict, registry_id: str, target_id: str, target_dir: Path) -> dict:
    """Install an npm package from the Registry into ``target_dir`` and describe it as a stdio server."""
    package_name = str(package.get("identifier") or "")
    version = str(package.get("version") or server.get("version") or "")
    if not _PACKAGE_NAME.fullmatch(package_name) or not _PACKAGE_VERSION.fullmatch(version):
        raise McpInstallError("The Registry returned an invalid npm package name or version.")
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(exist_ok=False)
    command, command_args = _npm_install_command(package_name, version, target_dir)

    def install_package() -> subprocess.CompletedProcess:
        return subprocess.run([command, *command_args], cwd=target_dir, capture_output=True, text=True, timeout=180)

    result = await asyncio.to_thread(install_package)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "npm install failed")[-3000:])
    executable = _package_entrypoint(target_dir / "node_modules" / Path(*package_name.split("/")))
    return {
        "id": target_id,
        "registry_id": registry_id,
        "name": server.get("title") or server.get("name") or package_name,
        "type": "stdio",
        "status": "stopped",
        "enabled": False,
        "command": "node",
        "args": [str(executable)],
        "env": {},
        "tools": [],
        "repository": _repository_url(server),
        "registry_version": version,
        "package": package_name,
        "install_path": str(target_dir),
    }


def save_new_server(state: ServerState, entry: dict) -> None:
    """Append ``entry`` to the saved MCP servers, refusing a Registry server that is already installed."""
    config = state.load_json_config("mcp_servers.json", DEFAULT_MCP_CONFIG)
    servers = list(config.get("servers", []))
    if any(item.get("registry_id") == entry["registry_id"] for item in servers):
        raise McpInstallError("This Registry MCP server is already installed.", 409)
    config["servers"] = [*servers, entry]
    state.save_json_config("mcp_servers.json", config)

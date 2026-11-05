"""POST /api/mcp/market/install: npm packages (scripts off, entry point checked) and remote endpoints."""

import io
import json
import subprocess
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import vera_agent.server.routes.mcp_market as mcp_market
from vera_agent.server.app import create_app


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    app_root.mkdir()
    test_client = TestClient(create_app(repo_root=app_root), base_url="http://127.0.0.1")
    test_client.app_root = app_root
    monkeypatch.setattr(mcp_market.shutil, "which", lambda _name: "/usr/bin/npm")
    return test_client


def _registry(monkeypatch, server: dict | None) -> None:
    payload = {"servers": [{"server": server}] if server else []}
    monkeypatch.setattr(mcp_market, "urlopen", lambda *_a, **_k: _Response(json.dumps(payload).encode()))


def _fake_npm(monkeypatch, manifest: dict | None, *, returncode: int = 0, create_entry: bool = True) -> list:
    """Replace `npm install` with a function that lays out node_modules/<package> and records the command."""
    calls: list = []

    def run(command, cwd, **_kwargs):
        calls.append(command)
        if returncode == 0 and manifest is not None:
            package_dir = Path(cwd) / "node_modules" / "@scope" / "tool"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
            if create_entry:
                (package_dir / "bin").mkdir()
                (package_dir / "bin" / "cli.js").write_text("// entry", encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr="npm ERR! boom")

    monkeypatch.setattr(mcp_market.subprocess, "run", run)
    return calls


NPM_SERVER = {
    "name": "io.example/tool",
    "title": "Example Tool",
    "version": "1.2.3",
    "repository": {"url": "https://github.com/example/tool"},
    "packages": [{"registryType": "npm", "identifier": "@scope/tool", "version": "1.2.3"}],
}


def test_npm_package_is_installed_without_scripts_and_registered_disabled(client, monkeypatch):
    _registry(monkeypatch, NPM_SERVER)
    calls = _fake_npm(monkeypatch, {"bin": {"tool": "bin/cli.js"}})

    response = client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["install_scripts"] == "disabled"
    server = body["server"]
    assert server["type"] == "stdio" and server["enabled"] is False and server["command"] == "node"
    assert server["package"] == "@scope/tool" and server["registry_version"] == "1.2.3"
    assert server["args"][0].endswith("cli.js") and Path(server["args"][0]).is_file()
    assert any("--ignore-scripts" in str(part) for part in calls[0]) and any(
        "@scope/tool@1.2.3" in str(p) for p in calls[0]
    )
    saved = json.loads((client.app_root / ".agents" / "mcp_servers.json").read_text(encoding="utf-8"))
    assert saved["servers"] == [server]


@pytest.mark.parametrize(
    ("package", "fragment"),
    [
        ({"registryType": "npm", "identifier": "bad name; rm -rf /", "version": "1.0.0"}, "invalid npm package name"),
        ({"registryType": "npm", "identifier": "@scope/tool", "version": "1.0.0 && x"}, "invalid npm package name"),
    ],
)
def test_unsafe_package_names_and_versions_never_reach_npm(client, monkeypatch, package, fragment):
    _registry(monkeypatch, {**NPM_SERVER, "packages": [package]})
    calls = _fake_npm(monkeypatch, {"bin": "bin/cli.js"})

    response = client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"})

    assert response.status_code == 400 and fragment in response.json()["error"]
    assert calls == []


@pytest.mark.parametrize(
    ("manifest", "returncode", "create_entry", "fragment"),
    [
        ({"name": "tool"}, 0, True, "command-line entry point"),
        ({"bin": "../../escape.js"}, 0, True, "missing or escapes"),
        ({"bin": "bin/missing.js"}, 0, False, "missing or escapes"),
        (None, 1, True, "npm ERR! boom"),
    ],
)
def test_failed_installs_are_reported_and_leave_no_directory_behind(
    client, monkeypatch, manifest, returncode, create_entry, fragment
):
    _registry(monkeypatch, NPM_SERVER)
    _fake_npm(monkeypatch, manifest, returncode=returncode, create_entry=create_entry)

    response = client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"})

    assert response.status_code == 502 and fragment in response.json()["error"]
    assert not list((client.app_root / ".agents" / "mcp").glob("mcp_*"))
    assert not (client.app_root / ".agents" / "mcp_servers.json").exists() or not json.loads(
        (client.app_root / ".agents" / "mcp_servers.json").read_text(encoding="utf-8")
    ).get("servers")


def test_missing_npm_is_a_clear_error(client, monkeypatch):
    _registry(monkeypatch, NPM_SERVER)
    monkeypatch.setattr(mcp_market.shutil, "which", lambda _name: None)

    response = client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"})

    assert response.status_code == 502 and "npm is not installed" in response.json()["error"]


@pytest.mark.parametrize(
    ("remote", "fragment"),
    [
        ({"type": "streamable-http", "url": "http://example.com/mcp"}, "credential-free HTTPS"),
        ({"type": "streamable-http", "url": "https://user:pw@example.com/mcp"}, "credential-free HTTPS"),
        ({"type": "sse", "url": "https://example.com/mcp"}, "credential-free HTTPS"),
    ],
)
def test_unsafe_remote_endpoints_are_refused(client, monkeypatch, remote, fragment):
    _registry(monkeypatch, {**NPM_SERVER, "packages": [], "remotes": [remote]})

    response = client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"})

    assert response.status_code == 400 and fragment in response.json()["error"]


def test_unknown_server_and_bad_ids_are_rejected(client, monkeypatch):
    _registry(monkeypatch, None)

    assert client.post("/api/mcp/market/install", json={"registry_id": "nope"}).status_code == 404
    assert client.post("/api/mcp/market/install", json={"registry_id": ""}).status_code == 400
    assert client.post("/api/mcp/market/install", json={"registry_id": "x" * 201}).status_code == 400


def test_installing_the_same_registry_server_twice_is_a_conflict(client, monkeypatch):
    _registry(monkeypatch, NPM_SERVER)
    _fake_npm(monkeypatch, {"bin": "bin/cli.js"})
    assert client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"}).status_code == 200

    assert client.post("/api/mcp/market/install", json={"registry_id": "io.example/tool"}).status_code == 409

"""MCP server registry and Registry market routes.

Routes: GET/POST /api/mcp/servers, PUT/DELETE /api/mcp/servers/{id},
PATCH /api/mcp/servers/{id}/toggle, POST /api/mcp/servers/{id}/restart,
GET /api/mcp/market, POST /api/mcp/market/install.

Configuration is application-scoped in `<projects_config_root>/.agents/mcp_servers.json`.
Market installs of npm packages run `npm install --ignore-scripts` into a local
directory; remote entries must use HTTPS.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.routes.mcp_market import (
    McpInstallError,
    fetch_registry_server,
    npm_entry,
    remote_entry,
    save_new_server,
)
from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.mcp")

DEFAULT_MCP_CONFIG = {"servers": []}
_MCP_MARKET_CACHE: dict[str, tuple[float, dict]] = {}
_MCP_MARKET_CACHE_TTL_SECONDS = 21_600
_MCP_MARKET_CACHE_VERSION = 2


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _load_mcp_config(state: ServerState) -> dict:
    return state.load_json_config("mcp_servers.json", DEFAULT_MCP_CONFIG)


async def get_mcp_servers(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = _load_mcp_config(state)
    return JSONResponse(cfg)


async def create_mcp_server(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    cfg = _load_mcp_config(state)
    servers = list(cfg.get("servers", []))

    sid = body.get("id") or f"mcp_{uuid.uuid4().hex[:8]}"
    registry_id = body.get("registry_id")
    if (
        not isinstance(sid, str)
        or not sid
        or any(
            server.get("id") == sid or (registry_id and server.get("registry_id") == registry_id) for server in servers
        )
    ):
        return JSONResponse({"error": "MCP server ID is invalid or already exists."}, status_code=409)
    enabled = body.get("enabled", False) is True
    server_entry = {
        "id": sid,
        "name": body.get("name", sid),
        "type": body.get("type", "local"),
        "status": "running" if enabled else "stopped",
        "enabled": enabled,
        "command": body.get("command", ""),
        "args": body.get("args", []),
        "env": body.get("env", {}),
        "tools": body.get("tools", []),
    }
    for field in ("url", "transport", "repository", "registry_version", "registry_id", "headers"):
        if field in body:
            server_entry[field] = body[field]
    servers.append(server_entry)
    cfg["servers"] = servers
    state.save_json_config("mcp_servers.json", cfg)
    return JSONResponse({"status": "ok", "server": server_entry})


async def update_mcp_server(request: Request) -> JSONResponse:
    """Updates existing MCP server config preserving data."""
    state = _get_state(request)
    server_id = request.path_params.get("server_id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    cfg = _load_mcp_config(state)
    servers = list(cfg.get("servers", []))
    target = next((s for s in servers if s.get("id") == server_id), None)
    if not target:
        return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

    for k, v in body.items():
        if k != "id":
            target[k] = v

    cfg["servers"] = servers
    state.save_json_config("mcp_servers.json", cfg)
    return JSONResponse({"status": "ok", "server": target})


async def toggle_mcp_server(request: Request) -> JSONResponse:
    state = _get_state(request)
    server_id = request.path_params["server_id"]
    cfg = _load_mcp_config(state)
    target = None
    for s in cfg.get("servers", []):
        if s["id"] == server_id:
            s["enabled"] = not s.get("enabled", True)
            s["status"] = "stopped" if not s["enabled"] else "running"
            target = s
            break

    if not target:
        return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

    state.save_json_config("mcp_servers.json", cfg)
    return JSONResponse({"status": "ok", "server": target})


async def restart_mcp_server(request: Request) -> JSONResponse:
    state = _get_state(request)
    server_id = request.path_params["server_id"]
    cfg = _load_mcp_config(state)
    found = False
    for s in cfg.get("servers", []):
        if s["id"] == server_id:
            s["status"] = "running"
            found = True
            break

    if not found:
        return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

    state.save_json_config("mcp_servers.json", cfg)
    return JSONResponse({"status": "ok", "server_id": server_id, "server_status": "running"})


async def delete_mcp_server(request: Request) -> JSONResponse:
    state = _get_state(request)
    server_id = request.path_params["server_id"]
    cfg = _load_mcp_config(state)
    original_len = len(cfg.get("servers", []))
    cfg["servers"] = [s for s in cfg.get("servers", []) if s["id"] != server_id]

    if len(cfg["servers"]) == original_len:
        return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

    state.save_json_config("mcp_servers.json", cfg)
    return JSONResponse({"status": "ok", "deleted_server_id": server_id})


async def get_mcp_market(request: Request) -> JSONResponse:
    state = _get_state(request)
    search = request.query_params.get("q", "").strip()
    params = {"limit": 10 if search else 50, "version": "latest"}
    if search:
        params["search"] = search[:100]
    cursor = request.query_params.get("cursor", "").strip()
    if cursor:
        params["cursor"] = cursor[:2048]
    cache_key = hashlib.sha256(f"{search}\0{cursor}".encode()).hexdigest()
    cache_root = getattr(state, "projects_config_root", state.root_path)
    cache_file = cache_root / ".agents" / "registries" / "mcp-market-cache" / f"{cache_key}.json"

    def fetch_registry() -> dict:
        cached = _MCP_MARKET_CACHE.get(cache_key)
        if cached and time.monotonic() - cached[0] < _MCP_MARKET_CACHE_TTL_SECONDS:
            return cached[1]
        try:
            disk_cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else None
            if (
                isinstance(disk_cache, dict)
                and disk_cache.get("version") == _MCP_MARKET_CACHE_VERSION
                and time.time() - float(disk_cache.get("fetched_at", 0)) < _MCP_MARKET_CACHE_TTL_SECONDS
                and isinstance(disk_cache.get("payload"), dict)
            ):
                payload = disk_cache["payload"]
                _MCP_MARKET_CACHE[cache_key] = (time.monotonic(), payload)
                return payload
        except (OSError, ValueError, TypeError):
            pass
        url = "https://registry.modelcontextprotocol.io/v0.1/servers?" + urlencode(params)
        req = UrlRequest(url, headers={"Accept": "application/json", "User-Agent": "VeraAgent/1.0"})
        # Registry search can be slower than the initial page; successful query
        # results are cached so subsequent searches return immediately.
        with urlopen(req, timeout=50) as response:
            payload = json.loads(response.read(2_000_000))
        records = payload.get("servers", [])
        market = []
        for record in records:
            entry = record.get("server", record)
            packages = entry.get("packages") or []
            remotes = entry.get("remotes") or []
            repo = entry.get("repository") or {}
            market.append(
                {
                    "id": entry.get("name", ""),
                    "name": entry.get("title") or entry.get("name", "MCP Server"),
                    "description": entry.get("description", ""),
                    "category": "远程服务" if remotes and not packages else "本地 / 远程",
                    "type": "remote" if remotes and not packages else "stdio",
                    "version": entry.get("version", ""),
                    "repository": repo.get("url", "") if isinstance(repo, dict) else str(repo),
                    "packages": packages,
                    "remotes": remotes,
                }
            )
        metadata = payload.get("metadata") or {}
        result = {
            "market": market,
            "source": "https://registry.modelcontextprotocol.io",
            "next_cursor": metadata.get("nextCursor") or None,
        }
        _MCP_MARKET_CACHE[cache_key] = (time.monotonic(), result)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file = cache_file.with_suffix(f".{os.getpid()}.tmp")
            temporary_file.write_text(
                json.dumps(
                    {"version": _MCP_MARKET_CACHE_VERSION, "fetched_at": time.time(), "payload": result},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            temporary_file.replace(cache_file)
        except OSError as error:
            logger.warning("Unable to persist MCP market cache: %s", error)
        return result

    try:
        result = await asyncio.to_thread(fetch_registry)
        return JSONResponse(result)
    except TimeoutError:
        logger.warning("MCP Registry request timed out for query %r", search)
        return JSONResponse(
            {
                "error": "MCP Registry search timed out. Loaded results are still available; try again shortly.",
                "market": [],
            },
            status_code=504,
        )
    except Exception as error:
        logger.warning("MCP Registry request failed: %s", error)
        return JSONResponse({"error": "Official MCP Registry is currently unavailable.", "market": []}, status_code=502)


async def install_mcp_market(request: Request) -> JSONResponse:
    """Install a version-pinned npm server (or a credential-free HTTPS remote) from the Official MCP Registry."""
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    registry_id = body.get("registry_id") if isinstance(body, dict) else None
    if not isinstance(registry_id, str) or not registry_id or len(registry_id) > 200:
        return JSONResponse({"error": "A Registry server ID is required."}, status_code=400)
    if any(item.get("registry_id") == registry_id for item in _load_mcp_config(state).get("servers", [])):
        return JSONResponse({"error": "This Registry MCP server is already installed."}, status_code=409)

    target_id = f"mcp_{uuid.uuid4().hex[:16]}"
    target_dir = state.projects_config_root / ".agents" / "mcp" / target_id
    try:
        server = await asyncio.to_thread(fetch_registry_server, registry_id)
        if not server:
            return JSONResponse({"error": "MCP server was not found in the Official Registry."}, status_code=404)
        package = next((item for item in server.get("packages", []) if item.get("registryType") == "npm"), None)
        if package:
            entry = await npm_entry(server, package, registry_id, target_id, target_dir)
            save_new_server(state, entry)
            return JSONResponse({"status": "ok", "server": entry, "install_scripts": "disabled"})
        entry = remote_entry(server, registry_id, target_id)
        save_new_server(state, entry)
        return JSONResponse({"status": "ok", "server": entry, "install_scripts": "not_applicable"})
    except McpInstallError as error:
        shutil.rmtree(target_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=error.status_code)
    except Exception as error:
        logger.warning("MCP Registry install failed for %s: %s", registry_id, error)
        shutil.rmtree(target_dir, ignore_errors=True)
        return JSONResponse({"error": str(error)}, status_code=502)


mcp_routes = [
    Route("/api/mcp/servers", get_mcp_servers, methods=["GET"]),
    Route("/api/mcp/servers", create_mcp_server, methods=["POST"]),
    Route("/api/mcp/servers/{server_id}", update_mcp_server, methods=["PUT"]),
    Route("/api/mcp/servers/{server_id}/toggle", toggle_mcp_server, methods=["PATCH"]),
    Route("/api/mcp/servers/{server_id}/restart", restart_mcp_server, methods=["POST"]),
    Route("/api/mcp/servers/{server_id}", delete_mcp_server, methods=["DELETE"]),
    Route("/api/mcp/market", get_mcp_market, methods=["GET"]),
    Route("/api/mcp/market/install", install_mcp_market, methods=["POST"]),
]

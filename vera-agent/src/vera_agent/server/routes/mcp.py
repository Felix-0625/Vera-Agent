"""Tool 7: MCP Servers bus management and ecosystem marketplace."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.mcp")

DEFAULT_MCP_CONFIG = {
    "servers": [
        {
            "id": "mcp-server-dev",
            "name": "mcp-server-dev",
            "type": "local",
            "status": "running",
            "enabled": True,
            "command": "python",
            "args": ["server.py"],
            "env": {},
            "tools": [
                {"name": "system_metrics", "description": "Inspect OS and Python runtime metrics"},
                {"name": "analyze_codebase", "description": "Analyze lines of code and file count"},
                {"name": "ping_diagnostic", "description": "High-precision latency and health check"},
            ],
        }
    ]
}


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _load_mcp_config(state: ServerState) -> dict:
    return state.load_json_config("mcp_servers.json", DEFAULT_MCP_CONFIG)


async def get_mcp_servers(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = _load_mcp_config(state)
    return JSONResponse(cfg)


async def scan_mcp_servers(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = _load_mcp_config(state)
    servers = list(cfg.get("servers", []))
    known_ids = {s["id"] for s in servers}

    ws_root = state.root_path
    candidate_dirs = [ws_root / "mcp-sever", ws_root / "mcp-server", ws_root / ".agents" / "mcp"]
    for c_dir in candidate_dirs:
        if c_dir.exists() and (c_dir / "server.py").exists():
            sid = c_dir.name
            if sid not in known_ids:
                servers.append({
                    "id": sid,
                    "name": sid,
                    "type": "local",
                    "status": "running",
                    "enabled": True,
                    "command": "python",
                    "args": ["server.py"],
                    "env": {},
                    "tools": [
                        {"name": "system_metrics", "description": "System metrics inspection"},
                        {"name": "analyze_codebase", "description": "Codebase analysis"},
                        {"name": "ping_diagnostic", "description": "Diagnostic health check"},
                    ],
                })
                known_ids.add(sid)

    cfg["servers"] = servers
    state.save_json_config("mcp_servers.json", cfg)
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
    server_entry = {
        "id": sid,
        "name": body.get("name", sid),
        "type": body.get("type", "local"),
        "status": "running",
        "enabled": True,
        "command": body.get("command", "python"),
        "args": body.get("args", ["server.py"]),
        "env": body.get("env", {}),
        "tools": body.get("tools", []),
    }
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
            s["status"] = "running" if s["enabled"] else "stopped"
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
    market_templates = [
        {
            "id": "drawio-mcp",
            "name": "Draw.io Architecture Diagram MCP",
            "description": "Export and render clean 2D system architecture diagrams in XML/SVG formats.",
            "category": "Design & Visualization",
            "type": "local",
        },
        {
            "id": "filesystem-mcp",
            "name": "Sandboxed File System Provider",
            "description": "Secure file reading, writing, and directory scanning capabilities for LLMs.",
            "category": "Core Primitives",
            "type": "local",
        },
        {
            "id": "sqlite-mcp",
            "name": "SQLite Analytics MCP",
            "description": "Directly execute SQL queries and inspect schema metrics inside local SQLite databases.",
            "category": "Database",
            "type": "local",
        },
        {
            "id": "github-mcp",
            "name": "GitHub PR & Issues Coordinator",
            "description": "Seamlessly inspect and update pull requests, issues, and commit annotations.",
            "category": "GitFlow Collaboration",
            "type": "cloud",
        },
        {
            "id": "brave-search-mcp",
            "name": "Brave Web Search & Doc Retriever",
            "description": "Perform live internet searches and retrieve the latest library documentations.",
            "category": "Web Intelligence",
            "type": "cloud",
        },
    ]
    return JSONResponse({"market": market_templates})


mcp_routes = [
    Route("/api/mcp/servers", get_mcp_servers, methods=["GET"]),
    Route("/api/mcp/servers", create_mcp_server, methods=["POST"]),
    Route("/api/mcp/servers/{server_id}", update_mcp_server, methods=["PUT"]),
    Route("/api/mcp/scan", scan_mcp_servers, methods=["POST"]),
    Route("/api/mcp/servers/{server_id}/toggle", toggle_mcp_server, methods=["PATCH"]),
    Route("/api/mcp/servers/{server_id}/restart", restart_mcp_server, methods=["POST"]),
    Route("/api/mcp/servers/{server_id}", delete_mcp_server, methods=["DELETE"]),
    Route("/api/mcp/market", get_mcp_market, methods=["GET"]),
]

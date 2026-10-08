"""Tool 3: Terminal execution endpoint for local development commands."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.terminal")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def exec_terminal_command(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    cmd = body.get("command", "").strip()
    if not cmd:
        return JSONResponse({"error": "command is required"}, status_code=400)

    timeout = min(int(body.get("timeout", 30)), 120)
    target_dir = state.root_path
    if body.get("group_id") and state.graph and body["group_id"] in state.graph.groups:
        target_dir = state.graph.groups[body["group_id"]].worktree_path
    elif body.get("cwd"):
        custom_cwd = Path(body["cwd"]).resolve()
        if custom_cwd.exists() and custom_cwd.is_dir():
            target_dir = custom_cwd

    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env=env,
        )
        return JSONResponse({
            "command": cmd,
            "cwd": str(target_dir),
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({
            "command": cmd,
            "cwd": str(target_dir),
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
        }, status_code=408)
    except Exception as e:
        return JSONResponse({
            "command": cmd,
            "cwd": str(target_dir),
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
        }, status_code=500)


terminal_routes = [
    Route("/api/terminal/exec", exec_terminal_command, methods=["POST"]),
]

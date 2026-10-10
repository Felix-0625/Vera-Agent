"""Tool 3: Terminal execution endpoint for local development commands."""

from __future__ import annotations

import asyncio
import codecs
import logging
import os
import shutil
import subprocess
from urllib.parse import urlsplit
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.terminal")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _get_project_root(state: ServerState, project_id: str | None) -> Path | None:
    if not project_id:
        return state.root_path
    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return None
    candidates = [project.get("path"), *(project.get("folders") or [])]
    return next((Path(path).resolve() for path in candidates if isinstance(path, str) and Path(path).is_dir()), None)


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
    target_dir = _get_project_root(state, body.get("project_id"))
    if target_dir is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
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


async def terminal_session(websocket: WebSocket) -> None:
    """Open a persistent local PowerShell process rooted in the selected workspace."""
    origin = websocket.headers.get("origin")
    if origin:
        origin_host = urlsplit(origin).hostname
        if origin_host not in {"localhost", "127.0.0.1", "::1"}:
            await websocket.close(code=1008, reason="Terminal sessions are local only")
            return

    state: ServerState = websocket.scope["app"].state.server_state
    group_id = websocket.query_params.get("group_id")
    project_id = websocket.query_params.get("project_id")
    target_dir = _get_project_root(state, project_id)
    if target_dir is None:
        await websocket.close(code=4404, reason="Unknown project")
        return
    if group_id:
        group = state.graph.groups.get(group_id) if state.graph else None
        if group is None:
            await websocket.close(code=4404, reason="Unknown project group")
            return
        target_dir = Path(group.worktree_path).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        await websocket.close(code=4404, reason="Project directory is unavailable")
        return

    shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not shell:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "找不到 Windows PowerShell（powershell.exe / pwsh.exe）。"})
        await websocket.close(code=1011)
        return

    await websocket.accept()
    utf8_setup = (
        "$utf8 = [System.Text.UTF8Encoding]::new($false); "
        "[Console]::InputEncoding = $utf8; "
        "[Console]::OutputEncoding = $utf8; "
        "$OutputEncoding = $utf8"
    )
    process: asyncio.subprocess.Process | None = None
    output_task: asyncio.Task[None] | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            shell,
            "-NoExit",
            "-Command",
            utf8_setup,
            cwd=str(target_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await websocket.send_json({
            "type": "connected",
            "shell": Path(shell).name,
            "cwd": str(target_dir),
        })

        async def forward_output() -> None:
            assert process is not None and process.stdout is not None
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            while chunk := await process.stdout.read(2048):
                text = decoder.decode(chunk)
                if text:
                    await websocket.send_json({"type": "output", "data": text})
            remaining = decoder.decode(b"", final=True)
            if remaining:
                await websocket.send_json({"type": "output", "data": remaining})

        output_task = asyncio.create_task(forward_output())
        while not output_task.done():
            receive_task = asyncio.create_task(websocket.receive_json())
            done, _ = await asyncio.wait({receive_task, output_task}, return_when=asyncio.FIRST_COMPLETED)
            if output_task in done:
                if not receive_task.done():
                    receive_task.cancel()
                    await asyncio.gather(receive_task, return_exceptions=True)
                break
            payload = receive_task.result()
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "input" and isinstance(payload.get("data"), str):
                assert process.stdin is not None
                process.stdin.write(payload["data"].encode("utf-8") + b"\r\n")
                await process.stdin.drain()
        await output_task
        if process.returncode is not None:
            await websocket.send_json({"type": "exit", "exit_code": process.returncode})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("PowerShell terminal session failed")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if output_task and not output_task.done():
            output_task.cancel()
            await asyncio.gather(output_task, return_exceptions=True)
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        try:
            await websocket.close()
        except Exception:
            pass


terminal_routes = [
    Route("/api/terminal/exec", exec_terminal_command, methods=["POST"]),
    WebSocketRoute("/api/terminal/session", terminal_session),
]

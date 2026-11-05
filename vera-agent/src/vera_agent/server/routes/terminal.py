"""Local terminal route.

Route: WebSocket /api/terminal/session (interactive PowerShell in the project directory).
The shell runs with the current OS user's privileges; there is no OS-level sandbox, so the
connection is refused for any non-loopback `Origin`.
"""

from __future__ import annotations

import asyncio
import codecs
import contextlib
import logging
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.terminal")

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
# Makes PowerShell read and write UTF-8 so Chinese output is not mangled on Windows.
UTF8_SETUP = (
    "$utf8 = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::InputEncoding = $utf8; "
    "[Console]::OutputEncoding = $utf8; "
    "$OutputEncoding = $utf8"
)


def _get_project_root(state: ServerState, project_id: str | None) -> Path | None:
    if not project_id:
        return state.root_path
    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return None
    candidates = [project.get("path"), *(project.get("folders") or [])]
    return next((Path(path).resolve() for path in candidates if isinstance(path, str) and Path(path).is_dir()), None)


def _resolve_working_dir(websocket: WebSocket) -> tuple[Path | None, str]:
    """The directory the shell starts in, or ``(None, reason)`` when the request names nothing usable."""
    state: ServerState = websocket.scope["app"].state.server_state
    target = _get_project_root(state, websocket.query_params.get("project_id"))
    if target is None:
        return None, "Unknown project"
    group_id = websocket.query_params.get("group_id")
    if group_id:
        group = state.graph.groups.get(group_id) if state.graph else None
        if group is None:
            return None, "Unknown project group"
        target = Path(group.worktree_path).resolve()
    if not target.is_dir():
        return None, "Project directory is unavailable"
    return target, ""


async def _forward_output(process: asyncio.subprocess.Process, websocket: WebSocket) -> None:
    """Stream the shell's stdout and stderr to the browser, decoding UTF-8 across chunk boundaries."""
    assert process.stdout is not None
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    while chunk := await process.stdout.read(2048):
        if text := decoder.decode(chunk):
            await websocket.send_json({"type": "output", "data": text})
    if remaining := decoder.decode(b"", final=True):
        await websocket.send_json({"type": "output", "data": remaining})


async def _pump_input(process: asyncio.subprocess.Process, websocket: WebSocket, output_task: asyncio.Task) -> None:
    """Write browser keystrokes to the shell until the shell exits or the browser disconnects."""
    assert process.stdin is not None
    while not output_task.done():
        receive_task = asyncio.create_task(websocket.receive_json())
        done, _ = await asyncio.wait({receive_task, output_task}, return_when=asyncio.FIRST_COMPLETED)
        if output_task in done:
            if not receive_task.done():
                receive_task.cancel()
                await asyncio.gather(receive_task, return_exceptions=True)
            return
        payload = receive_task.result()
        if isinstance(payload, dict) and payload.get("type") == "input" and isinstance(payload.get("data"), str):
            process.stdin.write(payload["data"].encode("utf-8") + b"\r\n")
            await process.stdin.drain()


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    """Ask the shell to exit, then kill it if it ignores the request for two seconds."""
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


async def terminal_session(websocket: WebSocket) -> None:
    """Open a persistent local PowerShell process rooted in the selected workspace."""
    origin = websocket.headers.get("origin")
    if origin and urlsplit(origin).hostname not in LOOPBACK_HOSTS:
        await websocket.close(code=1008, reason="Terminal sessions are local only")
        return

    target_dir, reason = _resolve_working_dir(websocket)
    if target_dir is None:
        await websocket.close(code=4404, reason=reason)
        return

    shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    await websocket.accept()
    if not shell:
        await websocket.send_json(
            {"type": "error", "message": "找不到 Windows PowerShell（powershell.exe / pwsh.exe）。"}
        )
        await websocket.close(code=1011)
        return

    process: asyncio.subprocess.Process | None = None
    output_task: asyncio.Task[None] | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            shell,
            "-NoExit",
            "-Command",
            UTF8_SETUP,
            cwd=str(target_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await websocket.send_json({"type": "connected", "shell": Path(shell).name, "cwd": str(target_dir)})
        output_task = asyncio.create_task(_forward_output(process, websocket))
        await _pump_input(process, websocket, output_task)
        await output_task
        # asyncio only fills in `returncode` once the exit has been awaited; without this the exit
        # message is sent only when the process happens to have been reaped already.
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(process.wait(), timeout=2)
        if process.returncode is not None:
            await websocket.send_json({"type": "exit", "exit_code": process.returncode})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("PowerShell terminal session failed")
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        if output_task and not output_task.done():
            output_task.cancel()
            await asyncio.gather(output_task, return_exceptions=True)
        if process:
            await _stop_process(process)
        with contextlib.suppress(Exception):
            await websocket.close()


terminal_routes = [
    WebSocketRoute("/api/terminal/session", terminal_session),
]

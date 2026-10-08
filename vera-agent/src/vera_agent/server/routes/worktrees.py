"""Tool 1: Git worktree status, diff inspection, file staging, discarding, checkpointing, and resetting."""

from __future__ import annotations

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.worktrees")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _resolve_target_dir(state: ServerState, group_id: str | None, wt_path_str: str | None) -> Path:
    if wt_path_str:
        return Path(wt_path_str).resolve()
    if group_id and state.graph and group_id in state.graph.groups:
        return state.graph.groups[group_id].worktree_path.resolve()
    return state.root_path.resolve()


async def get_worktree_diff(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.query_params.get("group_id")
    wt_path_str = request.query_params.get("worktree_path")
    target_dir = _resolve_target_dir(state, group_id, wt_path_str)

    # 1. Status porcelain
    code_st, stdout_st, stderr_st = state.run_git(["status", "--porcelain"], cwd=target_dir)
    staged: list[dict] = []
    unstaged: list[dict] = []
    untracked: list[str] = []

    for line in stdout_st.splitlines():
        if len(line) < 3:
            continue
        index_status = line[0]
        worktree_status = line[1]
        filepath = line[3:].strip()

        if index_status in ("M", "A", "D", "R"):
            staged.append({"file": filepath, "status": index_status})
        if worktree_status in ("M", "D"):
            unstaged.append({"file": filepath, "status": worktree_status})
        elif index_status == "?" and worktree_status == "?":
            untracked.append(filepath)

    # 2. Raw diffs
    _, diff_unstaged, _ = state.run_git(["diff"], cwd=target_dir)
    _, diff_staged, _ = state.run_git(["diff", "--cached"], cwd=target_dir)

    return JSONResponse({
        "cwd": str(target_dir),
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "diff_text": diff_unstaged,
        "diff_staged": diff_staged,
    })


async def stage_worktree_file(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    files = body.get("files") or ([body.get("file")] if body.get("file") else [])
    if not files:
        return JSONResponse({"error": "files list is required"}, status_code=400)

    target_dir = _resolve_target_dir(state, body.get("group_id"), body.get("worktree_path"))
    code, stdout, stderr = state.run_git(["add", *files], cwd=target_dir)
    if code != 0:
        return JSONResponse({"error": stderr or "git add failed", "returncode": code}, status_code=500)

    return JSONResponse({"status": "staged", "files": files})


async def discard_worktree_file(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    files = body.get("files") or ([body.get("file")] if body.get("file") else [])
    if not files:
        return JSONResponse({"error": "files list is required"}, status_code=400)

    target_dir = _resolve_target_dir(state, body.get("group_id"), body.get("worktree_path"))
    # Checkout/restore working tree changes
    code, stdout, stderr = state.run_git(["checkout", "--", *files], cwd=target_dir)
    if code != 0:
        # Fallback to git restore if checkout syntax fails
        code, stdout, stderr = state.run_git(["restore", *files], cwd=target_dir)

    return JSONResponse({"status": "discarded", "files": files, "returncode": code})


async def create_checkpoint(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    wt_path = body.get("worktree_path")
    group_id = body.get("group_id")
    if not wt_path and group_id and state.graph and group_id in state.graph.groups:
        wt_path = str(state.graph.groups[group_id].worktree_path)

    msg = body.get("message", "automated checkpoint")
    if not wt_path:
        return JSONResponse({"error": "worktree_path required"}, status_code=400)

    if not state.wt_manager:
        return JSONResponse({"error": "WorktreeManager not initialized"}, status_code=500)

    commit = state.wt_manager.create_checkpoint(wt_path, msg)
    return JSONResponse({"success": True, "commit": commit})


async def reset_worktree(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    wt_path = body.get("worktree_path")
    group_id = body.get("group_id")
    if not wt_path and group_id and state.graph and group_id in state.graph.groups:
        wt_path = str(state.graph.groups[group_id].worktree_path)

    hard = body.get("hard", True)
    if not wt_path:
        return JSONResponse({"error": "worktree_path required"}, status_code=400)

    if not state.wt_manager:
        return JSONResponse({"error": "WorktreeManager not initialized"}, status_code=500)

    success = state.wt_manager.reset_worktree(wt_path, hard=hard)
    return JSONResponse({"success": success})


worktree_routes = [
    Route("/api/worktrees/diff", get_worktree_diff, methods=["GET"]),
    Route("/api/worktrees/stage", stage_worktree_file, methods=["POST"]),
    Route("/api/worktrees/discard", discard_worktree_file, methods=["POST"]),
    Route("/api/worktrees/checkpoint", create_checkpoint, methods=["POST"]),
    Route("/api/worktrees/reset", reset_worktree, methods=["POST"]),
]

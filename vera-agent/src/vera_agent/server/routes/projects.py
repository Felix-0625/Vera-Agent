"""Module 2: Project workspace binding and projects history management."""

from __future__ import annotations

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState, get_git_branch

logger = logging.getLogger("vera_server.projects")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_projects(request: Request) -> JSONResponse:
    state = _get_state(request)
    proj_hist = state.load_json_config("projects_history.json", {"projects": []})
    return JSONResponse(proj_hist)


async def get_current_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    current_root = state.root_path
    return JSONResponse({
        "repo_root": str(current_root),
        "name": current_root.name,
        "is_git": (current_root / ".git").exists(),
        "active_branch": get_git_branch(current_root),
    })


async def bind_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    new_repo_root = body.get("repo_root") or body.get("path")
    if not new_repo_root:
        return JSONResponse({"error": "repo_root is required"}, status_code=400)

    target_path = Path(new_repo_root).resolve()
    if not target_path.exists() or not target_path.is_dir():
        return JSONResponse({"error": f"Path '{new_repo_root}' does not exist or is not a directory"}, status_code=400)

    state.init_workspace(target_path)
    state.sessions.clear()
    return JSONResponse({
        "status": "ok",
        "repo_root": str(state.root_path),
        "name": state.root_path.name,
        "active_branch": get_git_branch(state.root_path),
    })


async def delete_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    proj_id = request.path_params.get("project_id", "")
    proj_hist = state.load_json_config("projects_history.json", {"projects": []})
    projects = proj_hist.get("projects", [])
    before_len = len(projects)
    projects = [p for p in projects if p.get("id") != proj_id]
    if len(projects) == before_len:
        return JSONResponse({"error": f"Project '{proj_id}' not found"}, status_code=404)

    proj_hist["projects"] = projects
    state.save_json_config("projects_history.json", proj_hist)
    return JSONResponse({"status": "deleted", "project_id": proj_id})


project_routes = [
    Route("/api/projects", get_projects, methods=["GET"]),
    Route("/api/projects/current", get_current_project, methods=["GET"]),
    Route("/api/projects/bind", bind_project, methods=["POST"]),
    Route("/api/projects/{project_id}", delete_project, methods=["DELETE"]),
]

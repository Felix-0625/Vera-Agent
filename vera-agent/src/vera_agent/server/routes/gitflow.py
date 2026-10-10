"""Tool 9: GitFlow topology export, branch management, checkout, merge, and 3-Way merge review."""

from __future__ import annotations

import logging
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState, get_git_branch

logger = logging.getLogger("vera_server.gitflow")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _project_root(state: ServerState, project_id: str | None):
    if not project_id:
        return state.root_path
    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return None
    candidates = [project.get("path"), *(project.get("folders") or [])]
    return next((Path(path).resolve() for path in candidates if isinstance(path, str) and Path(path).is_dir()), None)


async def get_topology(request: Request) -> JSONResponse:
    state = _get_state(request)
    if not state.graph:
        return JSONResponse({"nodes": [], "edges": []})
    topo = state.graph.export_topology(graph_id="active_gitflow_topology")
    return JSONResponse(topo.model_dump())


async def get_branches(request: Request) -> JSONResponse:
    state = _get_state(request)
    root = _project_root(state, request.query_params.get("project_id"))
    if root is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    code, stdout, _ = state.run_git(["branch", "-a"], cwd=root)
    branches: list[dict] = []
    current_branch = get_git_branch(root)

    for line in stdout.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        is_curr = line_clean.startswith("*")
        name = line_clean.lstrip("* ").strip()
        if "->" in name:  # remote HEAD pointer like origin/HEAD -> origin/main
            continue
        branches.append({
            "name": name,
            "is_current": is_curr or (name == current_branch),
            "is_remote": name.startswith("remotes/"),
        })

    return JSONResponse({
        "current_branch": current_branch,
        "branches": branches,
    })


async def create_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    branch_name = body.get("branch_name")
    start_point = body.get("start_point", "HEAD")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["branch", branch_name, start_point], cwd=root)
    if code != 0:
        return JSONResponse({"error": stderr or "Failed to create branch"}, status_code=500)

    return JSONResponse({"status": "created", "branch_name": branch_name, "start_point": start_point})


async def delete_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    root = _project_root(state, request.query_params.get("project_id"))
    if root is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    branch_name = request.path_params.get("branch_name", "")
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["branch", "-D", branch_name], cwd=root)
    if code != 0:
        return JSONResponse({"error": stderr or f"Failed to delete branch {branch_name}"}, status_code=500)

    return JSONResponse({"status": "deleted", "branch_name": branch_name})


async def checkout_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    branch_name = body.get("branch_name")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["checkout", branch_name], cwd=root)
    if code != 0:
        return JSONResponse({"error": stderr or f"Failed to checkout {branch_name}"}, status_code=500)

    return JSONResponse({"status": "checked_out", "branch_name": branch_name})


async def merge_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source = body.get("source_branch")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    if not source:
        return JSONResponse({"error": "source_branch is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["merge", source], cwd=root)
    return JSONResponse({
        "status": "merged" if code == 0 else "conflict_or_error",
        "returncode": code,
        "stdout": stdout,
        "stderr": stderr,
    })


async def merge_review(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source = body.get("source_branch")
    target = body.get("target_branch", "main")
    req_id = body.get("requester_thread_id", "web_client")
    rev_id = body.get("reviewer_thread_id", "web_reviewer")

    if not source:
        return JSONResponse({"error": "source_branch required"}, status_code=400)

    if not state.router:
        return JSONResponse({"error": "SessionRouter not initialized"}, status_code=500)

    review = await state.router.request_merge_review(
        source_branch=source,
        target_branch=target,
        requester_thread_id=req_id,
        reviewer_thread_id=rev_id,
    )
    return JSONResponse(review.model_dump())


gitflow_routes = [
    Route("/api/topology", get_topology, methods=["GET"]),
    Route("/api/branches", get_branches, methods=["GET"]),
    Route("/api/branches", create_branch, methods=["POST"]),
    Route("/api/branches/{branch_name:path}", delete_branch, methods=["DELETE"]),
    Route("/api/branches/checkout", checkout_branch, methods=["POST"]),
    Route("/api/branches/merge", merge_branch, methods=["POST"]),
    Route("/api/merge-review", merge_review, methods=["POST"]),
]

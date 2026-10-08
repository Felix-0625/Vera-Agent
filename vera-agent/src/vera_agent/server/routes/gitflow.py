"""Tool 9: GitFlow topology export, branch management, checkout, merge, and 3-Way merge review."""

from __future__ import annotations

import logging
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState, get_git_branch

logger = logging.getLogger("vera_server.gitflow")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_topology(request: Request) -> JSONResponse:
    state = _get_state(request)
    if not state.graph:
        return JSONResponse({"nodes": [], "edges": []})
    topo = state.graph.export_topology(graph_id="active_gitflow_topology")
    return JSONResponse(topo.model_dump())


async def get_branches(request: Request) -> JSONResponse:
    state = _get_state(request)
    code, stdout, _ = state.run_git(["branch", "-a"])
    branches: list[dict] = []
    current_branch = get_git_branch(state.root_path)

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
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["branch", branch_name, start_point])
    if code != 0:
        return JSONResponse({"error": stderr or "Failed to create branch"}, status_code=500)

    return JSONResponse({"status": "created", "branch_name": branch_name, "start_point": start_point})


async def delete_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    branch_name = request.path_params.get("branch_name", "")
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["branch", "-D", branch_name])
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
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["checkout", branch_name])
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
    if not source:
        return JSONResponse({"error": "source_branch is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["merge", source])
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

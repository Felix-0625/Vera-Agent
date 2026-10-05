"""Starlette ASGI application serving the GitFlow dynamic graph API and agent control bus.

Adheres to Pi-agent minimalism and provides full REST endpoints for Web frontend:
- /api/health: System health and version
- /api/topology: React Flow standard topology JSON
- /api/groups: ProjectGroup and worktree creation
- /api/sessions/attach & detach: Hot-plug session orchestration
- /api/worktrees/checkpoint & reset: Aider-style checkpointing and disaster recovery
- /api/merge-review: In-memory 3-way PR merge review
- /api/code/check-syntax & search-symbols: Code intelligence APIs
- /api/skills: Dynamic skill listing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from minisweagent.session.graph import GitFlowGraph
from minisweagent.session.pipeline import HandoffPipeline
from minisweagent.session.router import SessionRouter
from minisweagent.session.worktree import WorktreeManager
from minisweagent.tools.code_tools import check_syntax_op, symbol_search_op
from minisweagent.tools.skill_tools import SkillManager


def create_app(
    repo_root: Path | str | None = None,
    graph: GitFlowGraph | None = None,
) -> Starlette:
    """Factory creating the ASGI application for multi-agent Web control."""
    root_path = Path(repo_root or Path.cwd()).resolve()
    wt_manager = WorktreeManager(repo_root=root_path)
    active_graph = graph or GitFlowGraph(repo_root=root_path, worktree_manager=wt_manager)
    router = SessionRouter(graph=active_graph)
    pipeline = HandoffPipeline(graph=active_graph)
    skill_mgr = SkillManager(root_dirs=[root_path])

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "2.4.6", "repo_root": str(root_path)})

    async def get_topology(request: Request) -> JSONResponse:
        topo = active_graph.export_topology(graph_id="active_gitflow_topology")
        return JSONResponse(topo.model_dump())

    async def create_group(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        group_id = body.get("group_id")
        branch_name = body.get("branch_name")
        base_branch = body.get("base_branch", "main")
        name = body.get("name")

        if not group_id or not branch_name:
            return JSONResponse({"error": "group_id and branch_name are required"}, status_code=400)

        group = active_graph.create_group(
            group_id=group_id,
            branch_name=branch_name,
            base_branch=base_branch,
            name=name,
        )
        return JSONResponse({
            "group_id": group.group_id,
            "branch": group.branch_name,
            "worktree_path": str(group.worktree_path),
        })

    async def attach_session(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        thread_id = body.get("thread_id")
        group_id = body.get("group_id")
        if not thread_id or not group_id:
            return JSONResponse({"error": "thread_id and group_id required"}, status_code=400)

        success = active_graph.attach_session_to_group(thread_id, group_id)
        return JSONResponse({"success": success})

    async def detach_session(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        thread_id = body.get("thread_id")
        if not thread_id:
            return JSONResponse({"error": "thread_id required"}, status_code=400)

        success = active_graph.detach_session(thread_id)
        return JSONResponse({"success": success})

    async def create_checkpoint(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        wt_path = body.get("worktree_path")
        msg = body.get("message", "automated checkpoint")
        if not wt_path:
            return JSONResponse({"error": "worktree_path required"}, status_code=400)

        commit = wt_manager.create_checkpoint(wt_path, msg)
        return JSONResponse({"success": True, "commit": commit})

    async def reset_worktree(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        wt_path = body.get("worktree_path")
        hard = body.get("hard", True)
        if not wt_path:
            return JSONResponse({"error": "worktree_path required"}, status_code=400)

        success = wt_manager.reset_worktree(wt_path, hard=hard)
        return JSONResponse({"success": success})

    async def merge_review(request: Request) -> JSONResponse:
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

        review = await router.request_merge_review(
            source_branch=source,
            target_branch=target,
            requester_thread_id=req_id,
            reviewer_thread_id=rev_id,
        )
        return JSONResponse(review.model_dump())

    async def list_skills(request: Request) -> JSONResponse:
        skill_mgr.refresh()
        return JSONResponse({"skills": skill_mgr.list_skills()})

    async def check_syntax(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        code = body.get("code", "")
        valid, msg = check_syntax_op(code)
        return JSONResponse({"valid": valid, "message": msg})

    async def search_symbols(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        query = body.get("query", "")
        sym_type = body.get("symbol_type", "all")
        results = symbol_search_op(root_path, query=query, symbol_type=sym_type)
        return JSONResponse({"results": results})

    routes = [
        Route("/api/health", health, methods=["GET"]),
        Route("/api/topology", get_topology, methods=["GET"]),
        Route("/api/groups", create_group, methods=["POST"]),
        Route("/api/sessions/attach", attach_session, methods=["POST"]),
        Route("/api/sessions/detach", detach_session, methods=["POST"]),
        Route("/api/worktrees/checkpoint", create_checkpoint, methods=["POST"]),
        Route("/api/worktrees/reset", reset_worktree, methods=["POST"]),
        Route("/api/merge-review", merge_review, methods=["POST"]),
        Route("/api/skills", list_skills, methods=["GET"]),
        Route("/api/code/check-syntax", check_syntax, methods=["POST"]),
        Route("/api/code/search-symbols", search_symbols, methods=["POST"]),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    return Starlette(routes=routes, middleware=middleware)

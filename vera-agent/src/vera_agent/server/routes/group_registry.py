"""Group registry routes: /api/groups/{group_id}/registry and /api/groups/{group_id}/edges."""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_store import (
    _get_state,
    _project_root,
)
from vera_agent.session.registry import RegistryManager

logger = logging.getLogger("vera_server.groups")


async def get_group_registry(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    try:
        project_root = _project_root(state, request.query_params.get("project_id"))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    reg = RegistryManager(project_root).get_group_registry(group_id)
    if not reg:
        return JSONResponse({"error": f"Registry for group '{group_id}' not found"}, status_code=404)
    return JSONResponse(reg.model_dump())


async def add_group_edge(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source_tid = body.get("source_thread_id")
    target_tid = body.get("target_thread_id")
    relation = body.get("relation", "connected_to")
    if not source_tid or not target_tid:
        return JSONResponse({"error": "source_thread_id and target_thread_id required"}, status_code=400)

    if state.graph:
        state.graph.record_communication(source_tid, target_tid, label=relation)
    if state.registry_mgr:
        state.registry_mgr.add_edge(group_id, source_tid, target_tid, relation=relation)

    return JSONResponse(
        {
            "status": "ok",
            "source_thread_id": source_tid,
            "target_thread_id": target_tid,
            "relation": relation,
        }
    )


async def remove_group_edge(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source_tid = body.get("source_thread_id")
    target_tid = body.get("target_thread_id")
    if not source_tid or not target_tid:
        return JSONResponse({"error": "source_thread_id and target_thread_id required"}, status_code=400)

    if state.graph:
        state.graph.remove_communication(source_tid, target_tid)
    if state.registry_mgr:
        state.registry_mgr.remove_edge(group_id, source_tid, target_tid)

    return JSONResponse({"status": "ok", "removed": True})

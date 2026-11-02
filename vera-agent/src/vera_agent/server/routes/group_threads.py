"""Group member routes: GET/POST /api/groups/{group_id}/threads; project session storage."""

from __future__ import annotations

import logging
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_store import (
    _get_state,
    _load_group,
    _project_root,
    _save_group,
)
from vera_agent.session.registry import RegistryManager
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.groups")


async def get_group_threads(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.get_group(group_id)
    if not group:
        return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

    thread_list = []
    for tid in group.thread_ids:
        s = state.get_or_create_session(tid, group_id=group_id)
        thread_list.append(
            {
                "thread_id": s.thread_id,
                "title": s.title,
                "role": s.role,
                "is_pinned": s.is_pinned,
                "is_archived": s.is_archived,
                "cost": round(s.cost, 4),
                "n_calls": s.n_calls,
                "updated_at": s.updated_at,
            }
        )
    return JSONResponse({"group_id": group_id, "threads": thread_list})


async def create_group_thread(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    project_id = request.query_params.get("project_id")
    try:
        project_root = _project_root(state, project_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    group_record = _load_group(project_root, group_id)
    if group_record:
        try:
            body = await request.json()
        except Exception:
            body = {}
        title = str(body.get("title", "新建协作窗口")).strip() or "新建协作窗口"
        role = str(body.get("role", "agent")).strip() or "agent"
        node_id = f"agent_{uuid.uuid4().hex[:8]}"
        thread_id = f"th_{uuid.uuid4().hex[:12]}"
        session = ThreadSession(
            thread_id=thread_id,
            group_id=group_id,
            project_id=project_id or group_record.get("project_id"),
            role=role,
            title=title,
            metadata={
                "project_root": str(project_root),
                "group_mode": group_record.get("group_mode", "team"),
                "group_goal": group_record.get("goal", ""),
                "group_background": group_record.get("background", ""),
                "workflow_node_id": node_id,
                "responsibilities": [str(body.get("responsibilities", ""))] if body.get("responsibilities") else [],
                "allowed_tools": body.get("allowed_tools", []),
            },
        )
        session.save(state.get_session_file(session))
        state.sessions[thread_id] = session
        node = {
            "id": node_id,
            "type": "agent",
            "title": title,
            "role": role,
            "responsibilities": session.metadata["responsibilities"],
            "allowed_tools": session.metadata["allowed_tools"],
            "thread_id": thread_id,
            "position": body.get("position", {"x": 320, "y": 180}),
        }
        group_record.setdefault("nodes", []).append(node)
        group_record.setdefault("thread_ids", []).append(thread_id)
        _save_group(project_root, group_record)
        registry_mgr = RegistryManager(project_root)
        registry_mgr.register_agent(
            group_id,
            thread_id,
            title,
            role,
            session.metadata["responsibilities"],
            session.metadata["allowed_tools"],
            f".agents/sessions/{thread_id}.json",
        )
        registry = registry_mgr.get_group_registry(group_id)
        if registry:
            registry.workflow_nodes = group_record["nodes"]
            registry.workflow_edges = group_record.get("edges", [])
            registry_mgr.save_group_registry(registry)
        return JSONResponse(session.to_dict())
    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.get_group(group_id)
    if not group:
        return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        body = {}

    title = body.get("title", "New Task Thread")
    role = body.get("role", "main")
    thread_id = f"th_{uuid.uuid4().hex[:10]}"

    s = ThreadSession(
        thread_id=thread_id,
        group_id=group_id,
        role=role,
        title=title,
    )
    state.sessions[thread_id] = s
    group.add_thread(thread_id)
    state.graph.register_session(thread_id, role=role, group_id=group_id, title=title)
    s.save(state.get_sessions_dir() / f"{thread_id}.json")

    if state.registry_mgr:
        state.registry_mgr.register_agent(
            group_id=group_id,
            thread_id=thread_id,
            title=title,
            role=role,
            log_uri=f".agents/sessions/{thread_id}.json",
            status="idle",
        )

    return JSONResponse(s.to_dict())

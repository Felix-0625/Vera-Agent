"""Module 3: Project groups lifecycle, topology templates, provisioning, and explicit registry."""

from __future__ import annotations

import logging
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.session.templates import list_topology_templates, get_topology_template
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.groups")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_groups(request: Request) -> JSONResponse:
    state = _get_state(request)
    if not state.graph:
        return JSONResponse({"groups": []})

    groups_data = []
    for grp in state.graph.groups.values():
        g_dict = grp.to_dict()
        thread_list = []
        for tid in grp.thread_ids:
            s = state.get_or_create_session(tid, group_id=grp.group_id)
            thread_list.append({
                "thread_id": s.thread_id,
                "title": s.title,
                "role": s.role,
                "is_pinned": s.is_pinned,
                "is_archived": s.is_archived,
                "cost": round(s.cost, 4),
                "n_calls": s.n_calls,
                "message_count": len(s.messages),
                "updated_at": s.updated_at,
            })
        g_dict["threads"] = thread_list
        groups_data.append(g_dict)

    return JSONResponse({"groups": groups_data})


async def create_group(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    group_id = body.get("group_id") or f"grp_{uuid.uuid4().hex[:8]}"
    branch_name = body.get("branch_name")
    base_branch = body.get("base_branch", "main")
    name = body.get("name")

    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.create_group(
        group_id=group_id,
        branch_name=branch_name,
        base_branch=base_branch,
        name=name,
    )
    return JSONResponse(group.to_dict())


async def update_group(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.get_group(group_id)
    if not group:
        return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if "name" in body:
        group.name = str(body["name"])
    if "is_pinned" in body:
        group.is_pinned = bool(body["is_pinned"])
    if "is_archived" in body:
        group.is_archived = bool(body["is_archived"])

    return JSONResponse(group.to_dict())


async def delete_group(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.get_group(group_id)
    if not group:
        return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

    branch_name = group.branch_name
    state.graph.remove_group(group_id)
    if state.wt_manager:
        state.wt_manager.remove_worktree(branch_name, force=True)
    if state.registry_mgr:
        state.registry_mgr.delete_group_registry(group_id)

    return JSONResponse({"status": "ok", "deleted_group_id": group_id})


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
        thread_list.append({
            "thread_id": s.thread_id,
            "title": s.title,
            "role": s.role,
            "is_pinned": s.is_pinned,
            "is_archived": s.is_archived,
            "cost": round(s.cost, 4),
            "n_calls": s.n_calls,
            "updated_at": s.updated_at,
        })
    return JSONResponse({"group_id": group_id, "threads": thread_list})


async def create_group_thread(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
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


async def get_templates(request: Request) -> JSONResponse:
    return JSONResponse({"templates": list_topology_templates()})


async def provision_group(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    template_id = body.get("template_id", "supervisor_dev")
    tpl = get_topology_template(template_id)
    if not tpl:
        return JSONResponse({"error": f"Template '{template_id}' not found"}, status_code=404)

    group_name = body.get("group_name") or f"Group: {tpl.name}"
    branch_name = body.get("branch_name")
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    base_branch = body.get("base_branch", "main")
    goal = body.get("goal", "").strip() or "Execute assigned development tasks."
    group_id = body.get("group_id") or f"grp_{uuid.uuid4().hex[:8]}"

    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    group = state.graph.create_group(
        group_id=group_id,
        branch_name=branch_name,
        base_branch=base_branch,
        name=group_name,
        topology_type=tpl.topology_type,
        goal=goal,
    )

    role_to_thread_id: dict[str, str] = {}
    created_threads: list[ThreadSession] = []

    for idx, n_bp in enumerate(tpl.nodes):
        tid = f"th_{n_bp.role_key}_{uuid.uuid4().hex[:6]}"
        role_to_thread_id[n_bp.role_key] = tid

        rendered_prompt = n_bp.prompt_template.replace("{{goal}}", goal).replace("{{task}}", n_bp.title)

        session = ThreadSession(
            thread_id=tid,
            group_id=group_id,
            role=n_bp.role,
            title=n_bp.title,
            metadata={
                "role_key": n_bp.role_key,
                "responsibilities": n_bp.responsibilities,
                "allowed_tools": n_bp.allowed_tools,
                "system_prompt": rendered_prompt,
            },
        )

        if idx == 0:
            session.add_messages({
                "role": "user",
                "content": f"[SYSTEM INITIATIVE: Group Goal Activated]\n业务总目标：{goal}\n请按照你的岗位职责（{n_bp.title}）开始拆解方案并引导协作窗口开展工作。",
            })

        state.sessions[tid] = session
        group.add_thread(tid)
        state.graph.register_session(
            thread_id=tid,
            role=n_bp.role,
            group_id=group_id,
            title=n_bp.title,
        )
        session.save(state.get_sessions_dir() / f"{tid}.json")
        created_threads.append(session)

        if state.registry_mgr:
            state.registry_mgr.register_agent(
                group_id=group_id,
                thread_id=tid,
                title=n_bp.title,
                role=n_bp.role,
                responsibilities=n_bp.responsibilities,
                allowed_tools=n_bp.allowed_tools,
                log_uri=f".agents/sessions/{tid}.json",
                status="idle",
            )

    for e_bp in tpl.edges:
        s_tid = role_to_thread_id.get(e_bp.source_role)
        t_tid = role_to_thread_id.get(e_bp.target_role)
        if s_tid and t_tid:
            state.graph.record_communication(s_tid, t_tid, label=e_bp.relation)
            if state.registry_mgr:
                state.registry_mgr.add_edge(group_id, s_tid, t_tid, relation=e_bp.relation)

    if state.registry_mgr:
        state.registry_mgr.create_or_update_group(
            group_id=group_id,
            group_name=group_name,
            branch_name=branch_name,
            worktree_path=str(group.worktree_path),
            topology_type=tpl.topology_type,
            goal=goal,
        )

    reg = state.registry_mgr.get_group_registry(group_id) if state.registry_mgr else None
    return JSONResponse({
        "status": "ok",
        "group": group.to_dict(),
        "threads": [s.to_dict() for s in created_threads],
        "registry": reg.model_dump() if reg else {},
    })


async def get_group_registry(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    if not state.registry_mgr:
        return JSONResponse({"error": "RegistryManager not initialized"}, status_code=500)

    reg = state.registry_mgr.get_group_registry(group_id)
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

    return JSONResponse({
        "status": "ok",
        "source_thread_id": source_tid,
        "target_thread_id": target_tid,
        "relation": relation,
    })


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


group_routes = [
    Route("/api/groups", get_groups, methods=["GET"]),
    Route("/api/groups", create_group, methods=["POST"]),
    Route("/api/groups/{group_id}", update_group, methods=["PATCH"]),
    Route("/api/groups/{group_id}", delete_group, methods=["DELETE"]),
    Route("/api/groups/{group_id}/threads", get_group_threads, methods=["GET"]),
    Route("/api/groups/{group_id}/threads", create_group_thread, methods=["POST"]),
    Route("/api/templates/topology", get_templates, methods=["GET"]),
    Route("/api/groups/provision", provision_group, methods=["POST"]),
    Route("/api/groups/{group_id}/registry", get_group_registry, methods=["GET"]),
    Route("/api/groups/{group_id}/edges", add_group_edge, methods=["POST"]),
    Route("/api/groups/{group_id}/edges", remove_group_edge, methods=["DELETE"]),
]

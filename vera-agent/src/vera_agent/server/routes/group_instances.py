"""Instance creation routes: /api/groups/instances, /api/groups/compose, /api/groups/provision."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_composition import (
    create_composition_sessions,
    populate_composition_registry,
    validate_composition,
)
from vera_agent.server.routes.group_materialization import _materialize_group_sessions
from vera_agent.server.routes.group_store import (
    _get_state,
    _groups_dir,
    _project_root,
    _save_group,
    organization_tree_error,
)
from vera_agent.session.registry import RegistryManager
from vera_agent.session.templates import get_topology_template
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.groups")


async def create_group_instance(request: Request) -> JSONResponse:
    """Create a project-local orchestration and its ordinary, role-aware agent threads."""
    state = _get_state(request)
    try:
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse({"error": "Group request must be a JSON object."}, status_code=400)
        project_id = str(body.get("project_id", ""))
        project_root = _project_root(state, project_id)
    except (ValueError, TypeError) as exc:
        return JSONResponse({"error": str(exc) or "project_id is required"}, status_code=400)
    name = str(body.get("name", "")).strip()
    group_mode = body.get("group_mode")
    nodes, edges = body.get("nodes"), body.get("edges", [])
    goal = body.get("goal", body.get("description", ""))
    background = body.get("background", "")
    if (
        not name
        or group_mode not in {"workflow", "architecture"}
        or not isinstance(nodes, list)
        or not nodes
        or len(nodes) > 60
        or not isinstance(edges, list)
        or len(edges) > 120
    ):
        return JSONResponse(
            {"error": "name, workflow/architecture type, 1–60 nodes and at most 120 edges are required"},
            status_code=400,
        )
    if not isinstance(goal, str) or len(goal) > 20_000 or not isinstance(background, str) or len(background) > 50_000:
        return JSONResponse(
            {"error": "Project goal/background must be text within the configured size limits."}, status_code=400
        )
    ids = {str(node.get("id", "")) for node in nodes if isinstance(node, dict)}
    if (
        len(ids) != len(nodes)
        or "" in ids
        or any(
            not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids
            for edge in edges
        )
    ):
        return JSONResponse({"error": "Invalid node IDs or edges"}, status_code=400)
    if group_mode == "architecture" and (tree_error := organization_tree_error(nodes, edges)):
        return JSONResponse({"error": tree_error}, status_code=400)
    group_id = f"flow_{uuid.uuid4().hex[:10]}"
    record = {
        "group_id": group_id,
        "project_id": project_id,
        "project_path": str(project_root),
        "group_mode": group_mode,
        "name": name,
        "goal": goal,
        "background": background,
        "template_id": body.get("template_id"),
        "template_name": body.get("template_name", name),
        "topology_type": group_mode,
        "thread_ids": [],
        "nodes": nodes,
        "edges": edges,
        "layout": body.get("layout", {}),
        "is_pinned": False,
        "is_archived": False,
        "created_at": time.time(),
    }
    _materialize_group_sessions(state, project_root, record)
    _save_group(project_root, record)
    return JSONResponse({"group": record}, status_code=201)


async def compose_group(request: Request) -> JSONResponse:
    """Create a group only after the client submits its final composition."""
    state = _get_state(request)
    body = await _composition_body(request)
    if isinstance(body, JSONResponse):
        return body

    project_id = body.get("project_id")
    if not project_id:
        return JSONResponse({"error": "project_id is required"}, status_code=400)
    try:
        project_root = _project_root(state, project_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    name = str(body.get("name", "")).strip()
    goal = str(body.get("goal", "")).strip()
    group_mode = body.get("group_mode", "team")
    nodes = body.get("nodes", [])
    edges = body.get("edges", [])
    if not name or not goal:
        return JSONResponse({"error": "name and goal are required"}, status_code=400)
    if group_mode not in {"team", "workflow"}:
        return JSONResponse({"error": "group_mode must be 'team' or 'workflow'"}, status_code=400)
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 60 or not isinstance(edges, list) or len(edges) > 120:
        return JSONResponse({"error": "The composition must contain 1–60 nodes and at most 120 edges"}, status_code=400)

    agent_nodes = validate_composition(nodes, edges)
    if isinstance(agent_nodes, JSONResponse):
        return agent_nodes

    group_id = f"grp_{uuid.uuid4().hex[:10]}"
    thread_ids: list[str] = []
    created_session_files: list[Path] = []
    registry_mgr = RegistryManager(project_root)
    created_registry = False
    try:
        role_threads: dict[str, str] = {}
        create_composition_sessions(
            state,
            project_root,
            project_id,
            group_id,
            group_mode,
            goal,
            agent_nodes,
            thread_ids,
            created_session_files,
            role_threads,
        )

        group_record = {
            "group_id": group_id,
            "project_id": project_id,
            "project_path": str(project_root),
            "group_mode": group_mode,
            "name": name,
            "goal": goal,
            "template_id": body.get("template_id"),
            "template_name": body.get("template_name"),
            "topology_type": body.get("topology_type", "custom"),
            "branch_name": "",
            "worktree_path": str(project_root),
            "thread_ids": thread_ids,
            "nodes": nodes,
            "edges": edges,
            "layout": body.get("layout", {}),
            "is_pinned": False,
            "is_archived": False,
            "created_at": time.time(),
        }
        _save_group(project_root, group_record)
        created_registry = True
        registry_mgr.create_or_update_group(
            group_id=group_id,
            group_name=name,
            branch_name="",
            worktree_path=str(project_root),
            topology_type=str(group_record["topology_type"]),
            goal=goal,
        )
        registry = registry_mgr.get_group_registry(group_id)
        if registry:
            registry.project_id = project_id
            registry.group_mode = group_mode
            registry.template_id = group_record["template_id"]
            registry.workflow_nodes = nodes
            registry.workflow_edges = edges
            registry.layout = group_record["layout"] if isinstance(group_record["layout"], dict) else {}
            populate_composition_registry(state, registry, agent_nodes, role_threads, edges)
            registry_mgr.save_group_registry(registry)
        return JSONResponse(
            {
                "status": "created",
                "group": group_record,
                "threads": [state.sessions[tid].to_dict() for tid in thread_ids],
                "registry": registry.model_dump() if registry else {},
            }
        )
    except Exception as exc:
        for session_file in created_session_files:
            session_file.unlink(missing_ok=True)
        for thread_id in thread_ids:
            state.sessions.pop(thread_id, None)
        (_groups_dir(project_root) / f"{group_id}.json").unlink(missing_ok=True)
        if created_registry:
            registry_mgr.delete_group_registry(group_id)
        logger.exception("Group composition creation failed for %s", group_id)
        return JSONResponse({"error": f"Failed to create group: {exc}"}, status_code=500)


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
            session.add_messages(
                {
                    "role": "user",
                    "content": f"[SYSTEM INITIATIVE: Group Goal Activated]\n业务总目标：{goal}\n请按照你的岗位职责（{n_bp.title}）开始拆解方案并引导协作窗口开展工作。",
                }
            )

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
    return JSONResponse(
        {
            "status": "ok",
            "group": group.to_dict(),
            "threads": [s.to_dict() for s in created_threads],
            "registry": reg.model_dump() if reg else {},
        }
    )


async def _composition_body(request: Request) -> dict | JSONResponse:
    """Keep JSON decoding separate from the composition transaction."""
    try:
        return await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

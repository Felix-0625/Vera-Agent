"""Group lifecycle and route registration.

Owns /api/groups and /api/groups/{group_id}; registers sibling handlers for threads,
templates/topology, instances, runs, provision, compose, registry and edges.
Project records live in <project>/.agents/groups/.
"""

from __future__ import annotations

import json
import logging
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.routes.group_instances import compose_group, create_group_instance, provision_group
from vera_agent.server.routes.group_materialization import _materialize_group_sessions
from vera_agent.server.routes.group_store import (
    _get_state,
    _groups_dir,
    _load_group,
    _project_root,
    _save_group,
    organization_tree_error,
)
from vera_agent.server.routes.group_threads import create_group_thread, get_group_threads
from vera_agent.server.routes.runs import create_group_run, update_group_run
from vera_agent.server.routes.templates import get_templates, save_topology_template
from vera_agent.session.registry import RegistryEdge, RegistryManager

logger = logging.getLogger("vera_server.groups")


async def get_groups(request: Request) -> JSONResponse:
    state = _get_state(request)
    project_id = request.query_params.get("project_id")
    try:
        project_root = _project_root(state, project_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    groups_data = []
    group_dir = _groups_dir(project_root)
    if group_dir.exists():
        for group_file in group_dir.glob("*.json"):
            try:
                group = json.loads(group_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if group.get("group_mode") in {"workflow", "architecture"}:
                missing_agent_sessions = any(
                    isinstance(node, dict)
                    and node.get("type") == "agent"
                    and (
                        not node.get("thread_id")
                        or not (project_root / ".agents" / "sessions" / f"{node.get('thread_id')}.json").exists()
                    )
                    for node in group.get("nodes", [])
                )
                if missing_agent_sessions:
                    _materialize_group_sessions(state, project_root, group)
                    _save_group(project_root, group)
            thread_list = []
            for thread_id in group.get("thread_ids", []):
                session_path = project_root / ".agents" / "sessions" / f"{thread_id}.json"
                if session_path.exists():
                    try:
                        session = state.get_or_create_session(thread_id, group_id=group.get("group_id"))
                        thread_list.append(
                            {
                                "thread_id": session.thread_id,
                                "project_id": session.project_id,
                                "group_id": session.group_id,
                                "title": session.title,
                                "role": session.role,
                                "is_pinned": session.is_pinned,
                                "is_archived": session.is_archived,
                                "cost": round(session.cost, 4),
                                "n_calls": session.n_calls,
                                "message_count": len(session.messages),
                                "updated_at": session.updated_at,
                            }
                        )
                    except Exception:
                        continue
            group["threads"] = thread_list
            groups_data.append(group)
    # Preserve groups created by the legacy graph API for the currently mounted project.
    # New project-scoped groups live in the project directory and do not rely on this graph.
    if state.graph and project_root.resolve() == state.root_path.resolve():
        known_ids = {group.get("group_id") for group in groups_data}
        for legacy_group in state.graph.groups.values():
            if legacy_group.group_id in known_ids:
                continue
            group_data = legacy_group.to_dict()
            group_data["threads"] = []
            for thread_id in legacy_group.thread_ids:
                session = state.get_or_create_session(thread_id, group_id=legacy_group.group_id)
                group_data["threads"].append(
                    {
                        "thread_id": session.thread_id,
                        "project_id": session.project_id,
                        "group_id": session.group_id,
                        "title": session.title,
                        "role": session.role,
                        "is_pinned": session.is_pinned,
                        "is_archived": session.is_archived,
                        "cost": round(session.cost, 4),
                        "n_calls": session.n_calls,
                        "message_count": len(session.messages),
                        "updated_at": session.updated_at,
                    }
                )
            groups_data.append(group_data)
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
    try:
        project_root = _project_root(state, request.query_params.get("project_id"))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    group_record = _load_group(project_root, group_id)
    if group_record:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "Group update must be a JSON object."}, status_code=400)
        for field, limit in (("goal", 20_000), ("background", 50_000)):
            if field in body and (not isinstance(body[field], str) or len(body[field]) > limit):
                return JSONResponse(
                    {"error": f"{field} must be text within the configured size limit."}, status_code=400
                )
        for field in (
            "name",
            "goal",
            "background",
            "group_mode",
            "is_pinned",
            "is_archived",
            "nodes",
            "edges",
            "layout",
        ):
            if field in body:
                group_record[field] = body[field]
        nodes = group_record.get("nodes", [])
        edges = group_record.get("edges", [])
        if not isinstance(nodes, list) or len(nodes) > 60 or not isinstance(edges, list) or len(edges) > 120:
            return JSONResponse(
                {"error": "Group updates must contain at most 60 nodes and 120 edges."}, status_code=400
            )
        node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
        if any(
            not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids
            for edge in edges
        ):
            return JSONResponse({"error": "Every edge must connect two existing nodes"}, status_code=400)
        if group_record.get("group_mode") == "architecture" and (tree_error := organization_tree_error(nodes, edges)):
            return JSONResponse({"error": tree_error}, status_code=400)
        _materialize_group_sessions(state, project_root, group_record)
        _save_group(project_root, group_record)
        registry_mgr = RegistryManager(project_root)
        registry = registry_mgr.get_group_registry(group_id)
        if registry:
            registry.group_name = str(group_record.get("name", registry.group_name))
            registry.goal = str(group_record.get("goal", registry.goal))
            registry.workflow_nodes = nodes
            registry.workflow_edges = edges
            registry.layout = group_record.get("layout", {}) if isinstance(group_record.get("layout"), dict) else {}
            registry.edges = []
            thread_by_node = {
                node.get("id"): node.get("thread_id")
                for node in nodes
                if isinstance(node, dict) and node.get("thread_id")
            }
            for node in nodes:
                if not isinstance(node, dict) or node.get("type") != "agent" or not node.get("thread_id"):
                    continue
                agent = next((item for item in registry.agents if item.thread_id == node["thread_id"]), None)
                if agent:
                    agent.title = str(node.get("title", agent.title))
                    agent.role = str(node.get("role", agent.role))
                    agent.responsibilities = (
                        node.get("responsibilities", []) if isinstance(node.get("responsibilities"), list) else []
                    )
                    agent.allowed_tools = (
                        node.get("allowed_tools", []) if isinstance(node.get("allowed_tools"), list) else []
                    )
            for edge in edges:
                source_thread = thread_by_node.get(edge.get("source"))
                target_thread = thread_by_node.get(edge.get("target"))
                if source_thread and target_thread:
                    registry.edges.append(
                        RegistryEdge(
                            source_thread_id=source_thread,
                            target_thread_id=target_thread,
                            relation=str(edge.get("relation", "message")),
                        )
                    )
            registry_mgr.save_group_registry(registry)
        return JSONResponse(group_record)
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
    try:
        project_root = _project_root(state, request.query_params.get("project_id"))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    group_record = _load_group(project_root, group_id)
    if group_record:
        (_groups_dir(project_root) / f"{group_id}.json").unlink(missing_ok=True)
        RegistryManager(project_root).delete_group_registry(group_id)
        for thread_id in group_record.get("thread_ids", []):
            session_file = project_root / ".agents" / "sessions" / f"{thread_id}.json"
            if thread_id in state.sessions:
                state.sessions[thread_id].group_id = None
                state.sessions[thread_id].save(session_file)
            state.sessions.pop(thread_id, None)
        return JSONResponse({"status": "ok", "deleted_group_id": group_id})
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


group_routes = [
    Route("/api/groups", get_groups, methods=["GET"]),
    Route("/api/groups", create_group, methods=["POST"]),
    Route("/api/groups/{group_id}", update_group, methods=["PATCH"]),
    Route("/api/groups/{group_id}", delete_group, methods=["DELETE"]),
    Route("/api/groups/{group_id}/threads", get_group_threads, methods=["GET"]),
    Route("/api/groups/{group_id}/threads", create_group_thread, methods=["POST"]),
    Route("/api/templates/topology", get_templates, methods=["GET"]),
    Route("/api/templates/topology", save_topology_template, methods=["POST"]),
    Route("/api/groups/instances", create_group_instance, methods=["POST"]),
    Route("/api/groups/{group_id}/runs", create_group_run, methods=["POST"]),
    Route("/api/groups/{group_id}/runs/{run_id}", update_group_run, methods=["PATCH"]),
    Route("/api/groups/provision", provision_group, methods=["POST"]),
    Route("/api/groups/compose", compose_group, methods=["POST"]),
]

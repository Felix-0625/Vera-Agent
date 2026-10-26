"""Multi-agent groups: topology templates, workflow/architecture instances, and runs.

Routes:
- GET/POST /api/templates/topology: built-in plus custom topology templates
- POST /api/groups/instances: copy a template into a project-owned instance
- POST /api/groups/{group_id}/runs: create an isolated run (requires confirmation "Y")
- PATCH /api/groups/{group_id}/runs/{run_id}: record run/node status and outputs
- GET/POST /api/groups, PATCH/DELETE /api/groups/{group_id}: group lifecycle
- GET/POST /api/groups/{group_id}/threads: group member conversations
- POST /api/groups/provision, /api/groups/compose: create a group with its threads
- GET /api/groups/{group_id}/registry, POST/DELETE /api/groups/{group_id}/edges

Storage:
- custom templates: `<projects_config_root>/.agents/templates/topology/<template_id>.json`
- instances: `<project>/.agents/groups/<group_id>.json`
- runs: `<project>/.agents/runs/<group_id>/<run_id>.json`

Run scheduling happens in the UI, which calls the chat stream once per node and
PATCHes the run; this module validates state transitions and persists results.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.routes.group_store import (
    _get_state,
    _groups_dir,
    _load_group,
    _project_root,
    _save_group,
    organization_tree_error,
)
from vera_agent.server.routes.runs import create_group_run, update_group_run
from vera_agent.server.routes.templates import get_templates, save_topology_template
from vera_agent.server.state import ServerState
from vera_agent.session.registry import AgentRegistryEntry, RegistryEdge, RegistryManager
from vera_agent.session.templates import get_topology_template
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.groups")


def _materialize_group_sessions(state: ServerState, project_root: Path, group: dict[str, Any]) -> None:
    """Ensure each agent node has a persistent, independently chat-able project thread."""
    thread_ids = list(group.get("thread_ids", []))
    for node in group.get("nodes", []):
        if not isinstance(node, dict) or node.get("type") != "agent":
            continue
        thread_id = str(node.get("thread_id") or "")
        if thread_id and (project_root / ".agents" / "sessions" / f"{thread_id}.json").exists():
            session = state.get_or_create_session(thread_id, group_id=str(group["group_id"]))
            session.group_id = str(group["group_id"])
            session.project_id = str(group.get("project_id") or "") or session.project_id
            session.role = str(node.get("role") or session.role)
            session.title = str(node.get("title") or session.title)
            session.metadata.update(
                {
                    "project_root": str(project_root),
                    "group_mode": group.get("group_mode", "workflow"),
                    "group_goal": group.get("goal", ""),
                    "group_background": group.get("background", ""),
                    "workflow_node_id": str(node.get("id", "")),
                    "node_background": str(node.get("background", "")),
                    "responsibilities": node.get("responsibilities", [])
                    if isinstance(node.get("responsibilities", []), list)
                    else [],
                    "constraints": node.get("constraints", []) if isinstance(node.get("constraints", []), list) else [],
                    "output_spec": str(node.get("output_spec", "")),
                    "system_prompt": str(node.get("prompt_template", "")),
                    "allowed_tools": node.get("allowed_tools", [])
                    if isinstance(node.get("allowed_tools", []), list)
                    else [],
                }
            )
            session.save(state.get_session_file(session))
            if thread_id not in thread_ids:
                thread_ids.append(thread_id)
            continue
        thread_id = f"th_{uuid.uuid4().hex[:12]}"
        title = str(node.get("title") or "对话窗口").strip() or "对话窗口"
        role = str(node.get("role") or "agent").strip() or "agent"
        responsibilities = node.get("responsibilities", [])
        if not isinstance(responsibilities, list):
            responsibilities = [str(responsibilities)] if responsibilities else []
        allowed_tools = node.get("allowed_tools", [])
        if not isinstance(allowed_tools, list):
            allowed_tools = []
        session = ThreadSession(
            thread_id=thread_id,
            group_id=str(group["group_id"]),
            project_id=str(group.get("project_id") or "") or None,
            role=role,
            title=title,
            metadata={
                "project_root": str(project_root),
                "group_mode": group.get("group_mode", "workflow"),
                "group_goal": group.get("goal", ""),
                "group_background": group.get("background", ""),
                "workflow_node_id": str(node.get("id", "")),
                "responsibilities": responsibilities,
                "node_background": str(node.get("background", "")),
                "constraints": node.get("constraints", []) if isinstance(node.get("constraints", []), list) else [],
                "output_spec": str(node.get("output_spec", "")),
                "system_prompt": str(node.get("prompt_template", "")),
                "allowed_tools": allowed_tools,
            },
        )
        session.save(state.get_session_file(session))
        state.sessions[thread_id] = session
        node["thread_id"] = thread_id
        thread_ids.append(thread_id)
        RegistryManager(project_root).register_agent(
            str(group["group_id"]),
            thread_id,
            title,
            role,
            responsibilities,
            allowed_tools,
            f".agents/sessions/{thread_id}.json",
        )
    group["thread_ids"] = thread_ids
    registry = RegistryManager(project_root).get_group_registry(str(group["group_id"]))
    if registry:
        registry.group_name = str(group.get("name", registry.group_name))
        registry.goal = str(group.get("goal", registry.goal))
        registry.group_mode = str(group.get("group_mode", registry.group_mode))
        registry.template_id = group.get("template_id")
        registry.workflow_nodes = group.get("nodes", [])
        registry.workflow_edges = group.get("edges", [])
        RegistryManager(project_root).save_group_registry(registry)


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
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

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

    allowed_node_types = {
        "agent",
        "start",
        "input",
        "condition",
        "code",
        "tool",
        "http",
        "knowledge",
        "document",
        "variable",
        "aggregator",
        "template",
        "parallel",
        "loop",
        "iteration",
        "approval",
        "error",
        "output",
        "end",
    }
    node_ids: set[str] = set()
    agent_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            return JSONResponse({"error": "Each node must be an object"}, status_code=400)
        node_id = str(node.get("id", "")).strip()
        node_type = str(node.get("type", "")).strip()
        if not node_id or node_id in node_ids or node_type not in allowed_node_types:
            return JSONResponse({"error": f"Invalid or duplicate node: {node_id or '(missing id)'}"}, status_code=400)
        if not str(node.get("title", "")).strip():
            return JSONResponse({"error": f"Node '{node_id}' needs a title"}, status_code=400)
        node_ids.add(node_id)
        if node_type == "agent":
            agent_nodes.append(node)
    if not agent_nodes:
        return JSONResponse({"error": "A group needs at least one Agent conversation window"}, status_code=400)

    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            return JSONResponse({"error": "Every edge must connect two existing nodes"}, status_code=400)

    group_id = f"grp_{uuid.uuid4().hex[:10]}"
    thread_ids: list[str] = []
    created_session_files: list[Path] = []
    registry_mgr = RegistryManager(project_root)
    created_registry = False
    try:
        role_threads: dict[str, str] = {}
        for node in agent_nodes:
            thread_id = f"th_{uuid.uuid4().hex[:12]}"
            responsibilities = node.get("responsibilities", [])
            allowed_tools = node.get("allowed_tools", [])
            session = ThreadSession(
                thread_id=thread_id,
                group_id=group_id,
                project_id=project_id,
                role=str(node.get("role", node.get("role_key", "agent"))),
                title=str(node["title"]).strip(),
                metadata={
                    "project_root": str(project_root),
                    "group_mode": group_mode,
                    "group_goal": goal,
                    "workflow_node_id": node["id"],
                    "responsibilities": responsibilities if isinstance(responsibilities, list) else [],
                    "allowed_tools": allowed_tools if isinstance(allowed_tools, list) else [],
                    "system_prompt": str(node.get("prompt_template", "")),
                },
            )
            session_file = state.get_session_file(session)
            session.save(session_file)
            created_session_files.append(session_file)
            state.sessions[thread_id] = session
            thread_ids.append(thread_id)
            role_threads[node["id"]] = thread_id
            node["thread_id"] = thread_id

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
            for node in agent_nodes:
                session = state.sessions[node["thread_id"]]
                registry.agents.append(
                    AgentRegistryEntry(
                        thread_id=session.thread_id,
                        title=session.title,
                        role=session.role,
                        responsibilities=session.metadata["responsibilities"],
                        allowed_tools=session.metadata["allowed_tools"],
                        log_uri=f".agents/sessions/{session.thread_id}.json",
                        status="idle",
                    )
                )
            for edge in edges:
                source_thread = role_threads.get(edge.get("source"))
                target_thread = role_threads.get(edge.get("target"))
                if source_thread and target_thread:
                    registry.edges.append(
                        RegistryEdge(
                            source_thread_id=source_thread,
                            target_thread_id=target_thread,
                            relation=str(edge.get("relation", "message")),
                        )
                    )
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
    Route("/api/groups/{group_id}/registry", get_group_registry, methods=["GET"]),
    Route("/api/groups/{group_id}/edges", add_group_edge, methods=["POST"]),
    Route("/api/groups/{group_id}/edges", remove_group_edge, methods=["DELETE"]),
]

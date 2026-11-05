"""Instance creation route: POST /api/groups/instances."""

from __future__ import annotations

import time
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_materialization import _materialize_group_sessions
from vera_agent.server.routes.group_store import (
    _get_state,
    _project_root,
    _save_group,
    organization_tree_error,
)


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

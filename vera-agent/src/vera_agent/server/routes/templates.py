"""Topology template routes: GET/POST /api/templates/topology.

Built-in templates come from `session/templates.py`; custom templates are stored at
`<projects_config_root>/.agents/templates/topology/<template_id>.json`.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_store import (
    _get_state,
    organization_tree_error,
)
from vera_agent.session.templates import BUILTIN_TEMPLATES

logger = logging.getLogger("vera_server.groups")


async def get_templates(request: Request) -> JSONResponse:
    state = _get_state(request)
    template_dir = state.projects_config_root / ".agents" / "templates" / "topology"
    templates_by_id: dict[str, dict[str, Any]] = {}
    for template in BUILTIN_TEMPLATES.values():
        data = template.model_dump()
        for index, node in enumerate(data["nodes"]):
            node["id"] = node.get("role_key") or f"agent_{index + 1}"
            node["type"] = "agent"
        for edge in data["edges"]:
            edge["source"] = edge["source_role"]
            edge["target"] = edge["target_role"]
        templates_by_id[template.template_id] = data

    if template_dir.exists():
        for template_file in sorted(template_dir.glob("*.json")):
            try:
                data = json.loads(template_file.read_text(encoding="utf-8"))
                template_id = data.get("template_id")
                if isinstance(template_id, str) and template_id.strip():
                    templates_by_id[template_id] = data
            except (OSError, json.JSONDecodeError):
                continue
    return JSONResponse({"templates": list(templates_by_id.values())})


async def save_topology_template(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    name = str(body.get("name", "")).strip()
    nodes = body.get("nodes")
    edges = body.get("edges", [])
    if not name or not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
        return JSONResponse({"error": "name and a non-empty nodes array are required"}, status_code=400)
    node_ids = {str(node.get("id", "")) for node in nodes if isinstance(node, dict)}
    if len(node_ids) != len(nodes) or "" in node_ids:
        return JSONResponse({"error": "Template node IDs must be unique and non-empty"}, status_code=400)
    if any(
        not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids
        for edge in edges
    ):
        return JSONResponse({"error": "Every template edge must connect two existing nodes"}, status_code=400)
    if body.get("topology_type") == "architecture" and (tree_error := organization_tree_error(nodes, edges)):
        return JSONResponse({"error": tree_error}, status_code=400)
    template_id = str(body.get("template_id") or f"tpl_{uuid.uuid4().hex[:10]}")
    template = {
        "template_id": template_id,
        "name": name,
        "description": str(body.get("description", "")),
        "topology_type": str(body.get("topology_type", "custom")),
        "nodes": nodes,
        "edges": edges,
        "is_custom": True,
    }
    template_dir = state.projects_config_root / ".agents" / "templates" / "topology"
    template_dir.mkdir(parents=True, exist_ok=True)
    target = template_dir / f"{template_id}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    return JSONResponse({"status": "saved", "template": template}, status_code=201)

"""Shared helpers for group routes: state access, project resolution, and JSON persistence.

Instances are stored at `<project>/.agents/groups/<group_id>.json` and runs at
`<project>/.agents/runs/<group_id>/<run_id>.json`; writes go through a temporary file and an atomic replace.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from starlette.requests import Request

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.groups")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _project_root(state: ServerState, project_id: str | None) -> Path:
    return state.get_project_root(project_id)


def _groups_dir(project_root: Path) -> Path:
    return project_root / ".agents" / "groups"


def _load_group(project_root: Path, group_id: str) -> dict[str, Any] | None:
    group_file = _groups_dir(project_root) / f"{group_id}.json"
    if not group_file.exists():
        return None
    try:
        return json.loads(group_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_group(project_root: Path, group: dict[str, Any]) -> None:
    group_dir = _groups_dir(project_root)
    group_dir.mkdir(parents=True, exist_ok=True)
    target = group_dir / f"{group['group_id']}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(group, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def _save_run(run_file: Path, run: dict[str, Any]) -> None:
    run_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = run_file.with_name(f"{run_file.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(run_file)


def organization_tree_error(nodes: list[Any], edges: list[Any]) -> str | None:
    """Return why ``edges`` are not a valid organization tree, or None.

    Organizations (``group_mode == "architecture"``) are reporting hierarchies: every edge points
    from a superior to a subordinate agent, each role has at most one superior, there is exactly
    one top role, and there are no cycles. Workflows allow general graphs and are not checked here.
    """
    agents = {node.get("id") for node in nodes if isinstance(node, dict) and node.get("type", "agent") == "agent"}
    if len(agents) != len([node for node in nodes if isinstance(node, dict)]):
        return "组织架构只能包含职责窗口，不能包含判断或循环节点。"
    parents: dict[str, str] = {}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source == target:
            return "组织架构中的职责窗口不能指向自己。"
        if target in parents:
            return "每个职责窗口只能有一个直接上级。"
        parents[target] = source
    roots = [node_id for node_id in agents if node_id not in parents]
    if len(roots) != 1:
        return "组织架构必须且只能有一个顶层职责窗口；请通过“添加下级 / 添加同级”建立上下级关系。"
    for node_id in agents:
        seen = set()
        while node_id in parents:
            if node_id in seen:
                return "组织架构的上下级关系不能形成循环。"
            seen.add(node_id)
            node_id = parents[node_id]
    return None

"""Materialize project-owned group nodes as persistent sessions and registry entries."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from vera_agent.server.state import ServerState
from vera_agent.session.registry import RegistryManager
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

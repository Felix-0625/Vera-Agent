"""Validate composed topology and populate its project registry."""

import uuid
from pathlib import Path
from typing import Any

from starlette.responses import JSONResponse

from vera_agent.server.state import ServerState
from vera_agent.session.registry import AgentRegistryEntry, RegistryEdge
from vera_agent.session.thread import ThreadSession


def validate_composition(nodes: list, edges: list) -> list[dict] | JSONResponse:
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

    return agent_nodes


def populate_composition_registry(
    state: ServerState, registry: Any, agent_nodes: list[dict], role_threads: dict[str, str], edges: list[dict]
) -> None:
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


def create_composition_sessions(
    state: ServerState,
    project_root: Path,
    project_id: str,
    group_id: str,
    group_mode: str,
    goal: str,
    agent_nodes: list[dict],
    thread_ids: list[str],
    created_session_files: list[Path],
    role_threads: dict[str, str],
) -> None:
    """Track each created file immediately so the caller can roll back partial failures."""
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

"""Workflow/architecture run routes.

- POST /api/groups/{group_id}/runs: create an isolated run (requires confirmation "Y")
- PATCH /api/groups/{group_id}/runs/{run_id}: validate run/node transitions and persist outputs

Scheduling happens in the UI (`frontend/src/components/tools/workflowRunner.ts`); this module
only validates and stores what the scheduler reports.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from vera_agent.server.routes.group_store import (
    _get_state,
    _load_group,
    _project_root,
    _save_run,
)
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.groups")


async def create_group_run(request: Request) -> JSONResponse:
    """Issue one isolated run after explicit Y confirmation and permission check."""
    state = _get_state(request)
    group_id = request.path_params["group_id"]
    try:
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse({"error": "Run request must be a JSON object."}, status_code=400)
        project_id = str(body.get("project_id", ""))
        project_root = _project_root(state, project_id)
    except (ValueError, TypeError) as exc:
        return JSONResponse({"error": str(exc) or "project_id is required"}, status_code=400)
    group = _load_group(project_root, group_id)
    if not group or group.get("project_id") != project_id:
        return JSONResponse({"error": "流程实例不存在于当前项目"}, status_code=404)
    if body.get("confirmation") != "Y":
        return JSONResponse({"error": "执行前必须明确选择 Y"}, status_code=403)
    requested = body.get("node_ids", [])
    if not isinstance(requested, list) or any(not isinstance(node_id, str) for node_id in requested):
        return JSONResponse({"error": "node_ids must be a list of node IDs."}, status_code=400)
    known_node_ids = {str(node.get("id")) for node in group.get("nodes", []) if isinstance(node, dict)}
    if requested and not set(requested).issubset(known_node_ids):
        return JSONResponse({"error": "node_ids contains an unknown workflow node."}, status_code=400)
    input_text = body.get("input", "")
    if not isinstance(input_text, str) or not input_text.strip():
        return JSONResponse({"error": "A non-empty text input is required to start a run."}, status_code=400)
    if len(input_text) > 100_000:
        return JSONResponse({"error": "Run input exceeds 100000 characters."}, status_code=413)
    nodes = [node for node in group.get("nodes", []) if (not requested or node.get("id") in requested)]
    if not nodes:
        return JSONResponse({"error": "请选择至少一个对话窗口"}, status_code=400)
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    sessions = []
    for node in nodes:
        thread_id = f"th_{uuid.uuid4().hex[:12]}"
        node_prompt = str(node.get("prompt_template", "")).strip()
        session = ThreadSession(
            thread_id=thread_id,
            group_id=group_id,
            project_id=project_id,
            role=str(node.get("role", "agent")),
            title=f"{node.get('title', 'Agent')} · {run_id}",
            metadata={
                "project_root": str(project_root),
                "group_mode": group.get("group_mode"),
                "group_goal": group.get("goal", ""),
                "group_background": group.get("background", ""),
                "workflow_node_id": node["id"],
                "workflow_run_id": run_id,
                "responsibilities": node.get("responsibilities", []),
                "node_background": str(node.get("background", "")),
                "constraints": node.get("constraints", []) if isinstance(node.get("constraints", []), list) else [],
                "output_spec": str(node.get("output_spec", "")),
                "allowed_tools": ["__orchestration_control__"]
                if node.get("type") in {"condition", "loop"}
                else node.get("allowed_tools", []),
                "workflow_control": node.get("type") in {"condition", "loop"},
                "workflow_node_type": node.get("type", "agent"),
                "system_prompt": node_prompt,
                "isolated_run": True,
            },
        )
        session.save(state.get_session_file(session))
        state.sessions[thread_id] = session
        sessions.append(
            {"node_id": node["id"], "thread_id": thread_id, "title": node["title"], "prompt_template": node_prompt}
        )
    run = {
        "run_id": run_id,
        "group_id": group_id,
        "project_id": project_id,
        "status": "ready",
        "input": input_text,
        "sessions": sessions,
        "created_at": time.time(),
        "nodes": [{"node_id": node["id"], "status": "pending", "output": "", "inputs": []} for node in nodes],
        "events": [{"type": "run_created", "at": time.time()}],
    }
    run_dir = project_root / ".agents" / "runs" / group_id
    _save_run(run_dir / f"{run_id}.json", run)
    return JSONResponse({"run": run}, status_code=201)


async def update_group_run(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id, run_id = request.path_params["group_id"], request.path_params["run_id"]
    project_id = request.query_params.get("project_id")
    try:
        project_root = _project_root(state, project_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    group = _load_group(project_root, group_id)
    if not group or group.get("project_id") != project_id:
        return JSONResponse({"error": "流程实例不存在于当前项目"}, status_code=404)
    run_file = project_root / ".agents" / "runs" / group_id / f"{run_id}.json"
    if not run_file.exists():
        return JSONResponse({"error": "Run not found"}, status_code=404)
    try:
        run = json.loads(run_file.read_text(encoding="utf-8"))
        body = await request.json()
    except (OSError, json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "Run record is invalid or request JSON is malformed."}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Run update must be a JSON object."}, status_code=400)
    if run.get("group_id") != group_id or run.get("project_id") != project_id:
        return JSONResponse({"error": "Run does not belong to this project instance."}, status_code=404)

    allowed_statuses = {"ready", "running", "completed", "failed", "cancelled"}
    old_status = run.get("status", "ready")
    next_status = body.get("status", old_status)
    transitions = {"ready": {"running", "failed", "cancelled"}, "running": {"completed", "failed", "cancelled"}}
    if not isinstance(next_status, str):
        return JSONResponse({"error": "Run status must be text."}, status_code=400)
    if next_status != old_status and (
        next_status not in allowed_statuses or next_status not in transitions.get(old_status, set())
    ):
        return JSONResponse({"error": f"Invalid run status transition: {old_status} -> {next_status}"}, status_code=409)

    changed_nodes: list[dict[str, Any]] = []
    previous_nodes = {item.get("node_id"): item for item in run.get("nodes", []) if isinstance(item, dict)}
    if "nodes" in body:
        submitted = body["nodes"]
        sessions = run.get("sessions", [])
        known_ids = {str(session.get("node_id")) for session in sessions if isinstance(session, dict)}
        statuses = {"pending", "running", "completed", "failed", "skipped"}
        if not isinstance(submitted, list) or len(submitted) > len(known_ids):
            return JSONResponse({"error": "Run nodes must be a bounded list of known node states."}, status_code=400)
        seen: set[str] = set()
        for item in submitted:
            if not isinstance(item, dict):
                return JSONResponse({"error": "Each run node state must be an object."}, status_code=400)
            node_id = str(item.get("node_id", ""))
            status = item.get("status")
            output = item.get("output", "")
            error = item.get("error", previous_nodes.get(str(item.get("node_id", "")), {}).get("error", ""))
            inputs = item.get("inputs", previous_nodes.get(node_id, {}).get("inputs", []))
            if (
                node_id not in known_ids
                or node_id in seen
                or not isinstance(status, str)
                or status not in statuses
                or not isinstance(output, str)
                or not isinstance(error, str)
                or len(error) > 4000
                or not isinstance(inputs, list)
                or len(inputs) > 50
            ):
                return JSONResponse(
                    {
                        "error": "Run node state has an unknown node, duplicate node, invalid status, or invalid text inputs/outputs."
                    },
                    status_code=400,
                )
            previous_status = previous_nodes.get(node_id, {}).get("status", "pending")
            allowed_node_transitions = {
                "pending": {"pending", "running", "completed", "failed", "skipped"},
                "running": {"running", "completed", "failed"},
                "completed": {"running", "completed"},
                "failed": {"failed"},
                "skipped": {"skipped"},
            }
            if status not in allowed_node_transitions.get(previous_status, set()):
                return JSONResponse(
                    {"error": f"Invalid node status transition: {previous_status} -> {status}"}, status_code=409
                )
            if len(output) > 200_000:
                return JSONResponse({"error": "A run node output exceeds 200000 characters."}, status_code=413)
            clean_inputs: list[dict[str, str]] = []
            input_size = 0
            for source in inputs:
                if not isinstance(source, dict) or any(
                    not isinstance(source.get(key), str) for key in ("node_id", "title", "output")
                ):
                    return JSONResponse(
                        {"error": "Each node input must include text node_id, title and output fields."},
                        status_code=400,
                    )
                if source["node_id"] not in known_ids:
                    return JSONResponse(
                        {"error": "Node input provenance references an unknown run node."}, status_code=400
                    )
                clean_source = {key: source[key] for key in ("node_id", "title", "output")}
                for key in ("relation", "label"):
                    if source.get(key) is not None:
                        if not isinstance(source[key], str):
                            return JSONResponse({"error": f"Node input {key} must be text."}, status_code=400)
                        clean_source[key] = source[key]
                input_size += sum(len(value) for value in clean_source.values())
                clean_inputs.append(clean_source)
            if input_size > 250_000:
                return JSONResponse({"error": "Node input provenance exceeds 250000 characters."}, status_code=413)
            seen.add(node_id)
            changed_nodes.append(
                {"node_id": node_id, "status": status, "output": output, "error": error, "inputs": clean_inputs}
            )
        merged_nodes = {**previous_nodes, **{item["node_id"]: item for item in changed_nodes}}
        run["nodes"] = [
            merged_nodes.get(
                str(session.get("node_id")), {"node_id": str(session.get("node_id")), "status": "pending", "output": ""}
            )
            for session in sessions
        ]

    if next_status == "completed" and any(
        item.get("status") not in {"completed", "skipped"} for item in run.get("nodes", [])
    ):
        return JSONResponse({"error": "A run cannot complete while any node is pending or running."}, status_code=409)
    if "final_output" in body:
        final_output = body["final_output"]
        if not isinstance(final_output, str) or len(final_output) > 200_000:
            return JSONResponse({"error": "final_output must be text of at most 200000 characters."}, status_code=400)
        run["final_output"] = final_output
    if "error" in body:
        error = body["error"]
        if not isinstance(error, str) or len(error) > 4000:
            return JSONResponse({"error": "Run error must be text of at most 4000 characters."}, status_code=400)
        run["error"] = error

    events = run.setdefault("events", [])
    # Node changes are recorded before the run status so a final "completed" event is always last.
    for node in changed_nodes:
        prior = previous_nodes.get(node["node_id"])
        if prior != node:
            events.append(
                {"type": "node_status", "node_id": node["node_id"], "status": node["status"], "at": time.time()}
            )
    if next_status != old_status:
        events.append({"type": "run_status", "from": old_status, "to": next_status, "at": time.time()})
        run["status"] = next_status
    if len(events) > 5000:
        del events[:-5000]
    _save_run(run_file, run)
    return JSONResponse({"run": run})

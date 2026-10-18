"""Validation of `POST /api/chat/stream` request bodies.

`parse_chat_request` checks every field and size limit before any session or model work starts,
and raises `ChatRequestError` with the HTTP status the route returns.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from starlette.responses import JSONResponse

from vera_agent.server.state import ServerState


class ChatRequestError(Exception):
    """A rejected chat request; carries the JSON error payload and HTTP status."""

    def __init__(self, payload: dict[str, Any], status_code: int = 400):
        super().__init__(payload.get("error", ""))
        self.payload = payload
        self.status_code = status_code

    def response(self) -> JSONResponse:
        return JSONResponse(self.payload, status_code=self.status_code)


@dataclass
class ChatRequest:
    """Validated fields of one chat turn (names mirror the JSON body)."""

    thread_id: Any
    content: Any
    model_id: Any
    rule_trigger: Any
    workflow_stage: Any
    workflow_control: Any
    workflow_context_text: Any
    attached_skills: Any
    attached_mcps: Any
    images: Any
    client_message_id: Any
    project_id: Any
    ephemeral: Any
    context_update: Any
    clean_context: Any


def _parse_attachment_ids(body: dict[str, Any], field: str) -> list[str]:
    values = body.get(field)
    if values is None:
        return []
    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must be a list of non-empty strings.")
    return list(dict.fromkeys(value.strip() for value in values))


def _validate_chat_attachments(state: ServerState, skills: list[str], mcps: list[str]) -> str | None:
    if skills:
        available_skills = {
            str(skill.get("name"))
            for skill in (state.skill_mgr.list_skills() if state.skill_mgr else [])
            if isinstance(skill, dict) and skill.get("name")
        }
        missing_skills = sorted(set(skills) - available_skills)
        if missing_skills:
            return f"Attached Skill is not installed: {', '.join(missing_skills)}"
        disabled_skills = set(
            state.load_json_config("skills_config.json", {"disabled_skills": []}).get("disabled_skills", [])
        )
        unavailable_skills = sorted(set(skills) & disabled_skills)
        if unavailable_skills:
            return f"Attached Skill is disabled: {', '.join(unavailable_skills)}"

    if mcps:
        configured = state.load_json_config("mcp_servers.json", {"servers": []}).get("servers", [])
        servers = {
            str(server.get("id")): server for server in configured if isinstance(server, dict) and server.get("id")
        }
        missing_mcps = sorted(set(mcps) - set(servers))
        if missing_mcps:
            return f"Attached MCP server is not configured: {', '.join(missing_mcps)}"
        disabled_mcps = sorted(server_id for server_id in mcps if not servers[server_id].get("enabled"))
        if disabled_mcps:
            return f"Attached MCP server is disabled: {', '.join(disabled_mcps)}"
    return None


def parse_chat_request(state: ServerState, body: dict[str, Any]) -> ChatRequest:
    """Validate a chat request body; raise ChatRequestError on the first invalid field."""
    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"
    content = body.get("content", "").strip()
    model_id = body.get("model_id")
    rule_trigger = body.get("rule_trigger")
    workflow_stage = body.get("workflow_stage")
    if workflow_stage is not None and workflow_stage not in {"supervisor_review", "control_decision"}:
        raise ChatRequestError({"error": "Unsupported workflow stage."}, status_code=400)
    workflow_control = body.get("workflow_control")
    if workflow_stage == "control_decision":
        if not isinstance(workflow_control, dict):
            raise ChatRequestError(
                {"error": "A structured workflow_control definition is required for control decisions."},
                status_code=400,
            )
        control_type = workflow_control.get("type")
        condition = workflow_control.get("condition")
        if (
            control_type not in {"condition", "loop"}
            or not isinstance(condition, str)
            or not condition.strip()
            or len(condition) > 10_000
        ):
            raise ChatRequestError(
                {
                    "error": "workflow_control must include a supported type and a non-empty condition of at most 10000 characters."
                },
                status_code=400,
            )
        if control_type == "loop":
            max_iterations = workflow_control.get("max_iterations")
            if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 20:
                raise ChatRequestError(
                    {"error": "A loop control must include max_iterations between 1 and 20."}, status_code=400
                )
    elif workflow_control is not None:
        raise ChatRequestError(
            {"error": "workflow_control is only accepted for control_decision turns."}, status_code=400
        )
    workflow_context = body.get("workflow_context")
    workflow_context_text = ""
    if workflow_context is not None:
        if not isinstance(workflow_context, dict) or not isinstance(workflow_context.get("task"), str):
            raise ChatRequestError(
                {"error": "workflow_context must contain a text task and upstream list."}, status_code=400
            )
        upstream_items = workflow_context.get("upstream")
        if not isinstance(upstream_items, list) or len(upstream_items) > 50:
            raise ChatRequestError(
                {"error": "workflow_context.upstream must contain at most 50 items."}, status_code=400
            )
        clean_upstream: list[dict[str, str]] = []
        context_size = len(workflow_context["task"])
        for item in upstream_items:
            if not isinstance(item, dict) or any(
                not isinstance(item.get(key), str) for key in ("node_id", "title", "output")
            ):
                raise ChatRequestError(
                    {"error": "Each workflow handoff must include text node_id, title and output fields."},
                    status_code=400,
                )
            clean_item = {key: item[key] for key in ("node_id", "title", "output")}
            for key in ("relation", "label"):
                if item.get(key) is not None:
                    if not isinstance(item[key], str):
                        raise ChatRequestError({"error": f"Workflow handoff {key} must be text."}, status_code=400)
                    clean_item[key] = item[key]
            if len(clean_item["output"]) > 100_000:
                raise ChatRequestError(
                    {"error": "A workflow handoff output exceeds 100000 characters."}, status_code=413
                )
            context_size += sum(len(value) for value in clean_item.values())
            if context_size > 250_000:
                raise ChatRequestError(
                    {"error": "Workflow handoff context exceeds 250000 characters."}, status_code=413
                )
            clean_upstream.append(clean_item)
        workflow_context_text = json.dumps(
            {"task": workflow_context["task"], "upstream": clean_upstream}, ensure_ascii=False, indent=2
        )
    if rule_trigger is not None and (
        not isinstance(rule_trigger, str) or rule_trigger not in {"goal", "plan", "learn", "grill-me"}
    ):
        raise ChatRequestError(
            {"error": "Unsupported chat command. Scheduled tasks must be created with a fixed execution time."},
            status_code=400,
        )
    try:
        attached_skills = _parse_attachment_ids(body, "attached_skills")
        attached_mcps = _parse_attachment_ids(body, "attached_mcps")
    except ValueError as error:
        raise ChatRequestError({"error": str(error)}, status_code=400)
    attachment_error = _validate_chat_attachments(state, attached_skills, attached_mcps)
    if attachment_error:
        raise ChatRequestError({"error": attachment_error}, status_code=409)
    images = body.get("images") or []
    client_message_id = str(body.get("client_message_id") or "")
    project_id = body.get("project_id")
    ephemeral = body.get("ephemeral") is True
    context_update = body.get("context_update") is True
    context_messages = body.get("context_messages") or []

    if ephemeral and not thread_id.startswith("side_"):
        raise ChatRequestError({"error": "Ephemeral chat IDs must use the side_ prefix."}, status_code=400)
    if not isinstance(context_messages, list) or len(context_messages) > 100:
        raise ChatRequestError({"error": "Context must contain at most 100 messages."}, status_code=400)
    clean_context: list[dict[str, str]] = []
    context_size = 0
    for message in context_messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
        ):
            raise ChatRequestError(
                {"error": "Context messages must have user or assistant roles and text content."}, status_code=400
            )
        context_content = message["content"][:30_000]
        context_size += len(context_content)
        if context_size > 250_000:
            raise ChatRequestError({"error": "Context is too large."}, status_code=413)
        clean_context.append({"role": message["role"], "content": context_content})

    if not isinstance(images, list) or len(images) > 4:
        raise ChatRequestError({"error": "At most four images can be attached to a message."}, status_code=400)
    for image in images:
        if not isinstance(image, dict) or not str(image.get("data_url", "")).startswith("data:image/"):
            raise ChatRequestError({"error": "Image attachments must be image data URLs."}, status_code=400)
        if len(str(image["data_url"])) > 11_500_000:
            raise ChatRequestError({"error": "Each image must be 8 MB or smaller."}, status_code=400)

    return ChatRequest(
        thread_id=thread_id,
        content=content,
        model_id=model_id,
        rule_trigger=rule_trigger,
        workflow_stage=workflow_stage,
        workflow_control=workflow_control,
        workflow_context_text=workflow_context_text,
        attached_skills=attached_skills,
        attached_mcps=attached_mcps,
        images=images,
        client_message_id=client_message_id,
        project_id=project_id,
        ephemeral=ephemeral,
        context_update=context_update,
        clean_context=clean_context,
    )

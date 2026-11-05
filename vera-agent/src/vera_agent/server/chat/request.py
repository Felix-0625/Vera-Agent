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


def _reject(message: str, status_code: int = 400) -> ChatRequestError:
    return ChatRequestError({"error": message}, status_code=status_code)


def _validate_workflow_control(workflow_stage: Any, workflow_control: Any) -> None:
    """A control-decision turn needs a condition (and a bounded iteration count for loops); no other turn may carry one."""
    if workflow_stage is not None and workflow_stage not in {"supervisor_review", "control_decision"}:
        raise _reject("Unsupported workflow stage.")
    if workflow_stage != "control_decision":
        if workflow_control is not None:
            raise _reject("workflow_control is only accepted for control_decision turns.")
        return
    if not isinstance(workflow_control, dict):
        raise _reject("A structured workflow_control definition is required for control decisions.")
    control_type = workflow_control.get("type")
    condition = workflow_control.get("condition")
    if control_type not in {"condition", "loop"} or not isinstance(condition, str) or not condition.strip():
        raise _reject(_BAD_CONDITION)
    if len(condition) > 10_000:
        raise _reject(_BAD_CONDITION)
    if control_type == "loop":
        max_iterations = workflow_control.get("max_iterations")
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 20:
            raise _reject("A loop control must include max_iterations between 1 and 20.")


_BAD_CONDITION = "workflow_control must include a supported type and a non-empty condition of at most 10000 characters."


def _clean_handoff(item: Any) -> dict[str, str]:
    """One upstream node's handoff reduced to its known text fields."""
    if not isinstance(item, dict) or any(not isinstance(item.get(key), str) for key in ("node_id", "title", "output")):
        raise _reject("Each workflow handoff must include text node_id, title and output fields.")
    clean = {key: item[key] for key in ("node_id", "title", "output")}
    for key in ("relation", "label"):
        if item.get(key) is not None:
            if not isinstance(item[key], str):
                raise _reject(f"Workflow handoff {key} must be text.")
            clean[key] = item[key]
    if len(clean["output"]) > 100_000:
        raise _reject("A workflow handoff output exceeds 100000 characters.", 413)
    return clean


def _workflow_context_text(workflow_context: Any) -> str:
    """The upstream handoffs of a workflow node as the JSON text injected into its prompt ("" when absent)."""
    if workflow_context is None:
        return ""
    if not isinstance(workflow_context, dict) or not isinstance(workflow_context.get("task"), str):
        raise _reject("workflow_context must contain a text task and upstream list.")
    upstream_items = workflow_context.get("upstream")
    if not isinstance(upstream_items, list) or len(upstream_items) > 50:
        raise _reject("workflow_context.upstream must contain at most 50 items.")
    clean_upstream: list[dict[str, str]] = []
    context_size = len(workflow_context["task"])
    for item in upstream_items:
        clean_item = _clean_handoff(item)
        context_size += sum(len(value) for value in clean_item.values())
        if context_size > 250_000:
            raise _reject("Workflow handoff context exceeds 250000 characters.", 413)
        clean_upstream.append(clean_item)
    return json.dumps({"task": workflow_context["task"], "upstream": clean_upstream}, ensure_ascii=False, indent=2)


def _clean_context_messages(context_messages: Any) -> list[dict[str, str]]:
    """Side-chat context: user/assistant text only, each message clipped to 30,000 characters."""
    if not isinstance(context_messages, list) or len(context_messages) > 100:
        raise _reject("Context must contain at most 100 messages.")
    clean: list[dict[str, str]] = []
    context_size = 0
    for message in context_messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
        ):
            raise _reject("Context messages must have user or assistant roles and text content.")
        content = message["content"][:30_000]
        context_size += len(content)
        if context_size > 250_000:
            raise _reject("Context is too large.", 413)
        clean.append({"role": message["role"], "content": content})
    return clean


def _validate_images(images: Any) -> None:
    if not isinstance(images, list) or len(images) > 4:
        raise _reject("At most four images can be attached to a message.")
    for image in images:
        if not isinstance(image, dict) or not str(image.get("data_url", "")).startswith("data:image/"):
            raise _reject("Image attachments must be image data URLs.")
        if len(str(image["data_url"])) > 11_500_000:
            raise _reject("Each image must be 8 MB or smaller.")


def parse_chat_request(state: ServerState, body: dict[str, Any]) -> ChatRequest:
    """Validate a chat request body; raise ChatRequestError on the first invalid field."""
    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"
    rule_trigger = body.get("rule_trigger")
    workflow_stage = body.get("workflow_stage")
    workflow_control = body.get("workflow_control")
    _validate_workflow_control(workflow_stage, workflow_control)
    workflow_context_text = _workflow_context_text(body.get("workflow_context"))
    if rule_trigger is not None and rule_trigger not in {"goal", "plan", "learn", "grill-me"}:
        raise _reject("Unsupported chat command. Scheduled tasks must be created with a fixed execution time.")
    try:
        attached_skills = _parse_attachment_ids(body, "attached_skills")
        attached_mcps = _parse_attachment_ids(body, "attached_mcps")
    except ValueError as error:
        raise _reject(str(error)) from error
    if attachment_error := _validate_chat_attachments(state, attached_skills, attached_mcps):
        raise _reject(attachment_error, 409)

    ephemeral = body.get("ephemeral") is True
    if ephemeral and not thread_id.startswith("side_"):
        raise _reject("Ephemeral chat IDs must use the side_ prefix.")
    clean_context = _clean_context_messages(body.get("context_messages") or [])
    images = body.get("images") or []
    _validate_images(images)

    return ChatRequest(
        thread_id=thread_id,
        content=body.get("content", "").strip(),
        model_id=body.get("model_id"),
        rule_trigger=rule_trigger,
        workflow_stage=workflow_stage,
        workflow_control=workflow_control,
        workflow_context_text=workflow_context_text,
        attached_skills=attached_skills,
        attached_mcps=attached_mcps,
        images=images,
        client_message_id=str(body.get("client_message_id") or ""),
        project_id=body.get("project_id"),
        ephemeral=ephemeral,
        context_update=body.get("context_update") is True,
        clean_context=clean_context,
    )

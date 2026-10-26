"""Assemble everything one chat turn needs before it starts streaming.

`prepare_turn` validates the request body, resolves the session, working directory, permission
policy, model and system prompt, and returns a `TurnContext` for `server/chat/turn.py`. Validation
failures raise `ChatRequestError` with the status the HTTP route returns, so the desktop route and
headless callers (the eval runner) share one setup path.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.memory.retrieve import Recall, recall, render_recall
from vera_agent.memory.service import load_memory_config, memory_service_for_state
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.models.utils.openai_multimodal import DEFAULT_MULTIMODAL_REGEX
from vera_agent.server.chat.control import ApprovalPolicy, InteractiveApprovalPolicy, TurnControl
from vera_agent.server.chat.prompt import build_system_prompt
from vera_agent.server.chat.request import ChatRequest, ChatRequestError, parse_chat_request
from vera_agent.server.model_profile import resolve_model_profile
from vera_agent.server.permissions import normalize_permissions_config
from vera_agent.server.state import ServerState
from vera_agent.server.user_context import load_context_settings
from vera_agent.session.registry import RegistryManager
from vera_agent.session.thread import ThreadSession
from vera_agent.telemetry.trace import TurnTracer


@dataclass
class TurnContext:
    """Resolved inputs and collaborators of one chat turn."""

    state: ServerState
    request: ChatRequest
    session: ThreadSession
    control: TurnControl
    approval_policy: ApprovalPolicy
    target_cwd: Path
    group_registry: RegistryManager | None
    context_settings: dict[str, Any]
    env: LocalEnvironment
    mode: str
    approval_actions: list[str]
    group_tools: Any
    tool_call_limit: int
    tool_call_budget: dict[str, Any]
    model_profile: dict[str, Any]
    model: Any
    agent: DefaultAgent
    system_prompt: str
    context_prompt_vars: dict[str, Any]
    control_response_format: Any
    forced_delegate: str | None
    is_control_decision: bool
    tracer: TurnTracer | None = None
    memory_recall: Recall | None = None
    mcp_tools: list[dict] = field(default_factory=list)
    mcp_dispatch: dict[str, tuple[Any, str]] = field(default_factory=dict)

    @property
    def thread_id(self) -> str:
        return self.request.thread_id

    @property
    def memory_tools_enabled(self) -> bool:
        """The model may call `remember_user`/`forget_user_memory` only in personal main conversations."""
        return (
            self.context_settings["memory_enabled"]
            and self.session.role == "main"
            and not self.request.ephemeral
            and not self.session.group_id
        )


def explicit_subagent_request(text: str) -> str | None:
    """Return the delegate when the user explicitly asks to run a subagent."""
    normalized = text.lower()
    agent_mention = r"(?:sub\s*agent|subagent|子智能体|子代理|研究员|审查员|reviewer)"
    action = r"(?:创建|启动|调用|委派|派出|运行|create|start|invoke|run|让.{0,4}执行)"
    if not (
        re.search(rf"{action}.{{0,16}}{agent_mention}", normalized)
        or re.search(rf"{agent_mention}.{{0,16}}{action}", normalized)
        or re.search(r"让.{0,4}(?:研究员|审查员|reviewer)", normalized)
    ):
        return None
    refusals = (
        "不要创建",
        "不要启动",
        "不要调用",
        "不需要创建",
        "不用创建",
        "don't create",
        "do not create",
        "don't invoke",
        "do not invoke",
    )
    if any(token in normalized for token in refusals):
        return None
    # Choose the reviewer only when the named agent is a reviewer (Chinese or English wording);
    # every other explicit subagent request defaults to the researcher.
    reviewer = re.search(
        r"审查员|reviewer|review\s*(?:sub\s*agent|subagent|agent)|(?:审查|评审|代码审查)(?:子智能体|子代理|智能体)",
        normalized,
    )
    return "delegate_review" if reviewer else "delegate_research"


def _resolve_session(state: ServerState, request: ChatRequest, body: dict[str, Any]) -> tuple[ThreadSession, bool]:
    """Return the turn's session and whether an ephemeral side session was created for it."""
    thread_id = request.thread_id
    created_ephemeral = False
    if request.ephemeral:
        session = state.sessions.get(thread_id)
        if session and not session.metadata.get("ephemeral"):
            raise ChatRequestError({"error": "The requested side conversation is not ephemeral."}, 409)
        if session is None:
            session = ThreadSession(
                thread_id=thread_id, role="side", title="临时侧边对话", metadata={"ephemeral": True}
            )
            state.sessions[thread_id] = session
            created_ephemeral = True
    else:
        session = state.get_or_create_session(thread_id)
    requested_project_id = str(request.project_id or session.project_id or "").strip()
    if requested_project_id:
        if session.project_id and session.project_id != requested_project_id:
            raise ChatRequestError({"error": "Conversation cannot be moved to a different project."}, 409)
        try:
            selected_project_root = state.get_project_root(requested_project_id)
        except ValueError as error:
            raise ChatRequestError({"error": str(error)}, 404) from error
        session.project_id = requested_project_id
        session.metadata.setdefault("project_root", str(selected_project_root))
    if body.get("group_id") and not session.group_id:
        session.group_id = body["group_id"]
        if state.graph and not request.ephemeral:
            state.graph.attach_session_to_group(thread_id, session.group_id)
    return session, created_ephemeral


def _check_workflow_stage(request: ChatRequest, session: ThreadSession) -> tuple[bool, bool]:
    """Return (is_supervisor_review, is_control_decision) after checking the stage is allowed here."""
    stage = request.workflow_stage
    isolated = session.metadata.get("isolated_run") is True
    is_supervisor_review = stage == "supervisor_review" and isolated
    is_control_decision = stage == "control_decision" and isolated
    if stage == "supervisor_review" and not is_supervisor_review:
        raise ChatRequestError({"error": "Supervisor review is only available for an isolated workflow run."}, 403)
    if stage == "control_decision" and not is_control_decision:
        raise ChatRequestError({"error": "Control decisions are only available to isolated workflow windows."}, 403)
    if is_control_decision and request.workflow_control.get("type") != session.metadata.get("workflow_node_type"):
        raise ChatRequestError({"error": "The control definition does not match this workflow node."}, 409)
    return is_supervisor_review, is_control_decision


def _target_cwd(state: ServerState, session: ThreadSession) -> Path:
    # Working directory: Worktree path of attached group if present, otherwise root_path
    target_cwd = Path(session.metadata.get("worktree_path") or session.metadata.get("project_root") or state.root_path)
    if session.group_id and state.graph and session.group_id in state.graph.groups:
        target_cwd = state.graph.groups[session.group_id].worktree_path
    return target_cwd


def _build_model(state: ServerState, request: ChatRequest) -> tuple[dict[str, Any], LitellmModel, int]:
    """Resolve the selected model, apply its saved runtime settings, and return its tool-call limit."""
    try:
        model_profile = resolve_model_profile(state, request.model_id or None)
    except ValueError as error:
        raise ChatRequestError({"error": str(error)}, 400) from error
    if request.images and model_profile["config"].get("supports_images") is False:
        raise ChatRequestError({"error": "The selected model is configured without image input support."}, 400)
    try:
        tool_call_limit = max(1, int(model_profile["config"].get("max_tool_calls") or 15))
    except (TypeError, ValueError):
        tool_call_limit = 15
    model = LitellmModel(
        model_name=model_profile["name"],
        model_kwargs=model_profile["model_kwargs"],
        dynamic_tool_names=[],
        allow_empty_tool_calls=True,
        multimodal_regex=DEFAULT_MULTIMODAL_REGEX,
    )
    model.context_window = model_profile["context_window"]
    return model_profile, model, tool_call_limit


def _seed_ephemeral_context(request: ChatRequest, session: ThreadSession, system_prompt: str, created: bool) -> None:
    if created:
        session.add_messages(
            {
                "role": "system",
                "content": system_prompt
                + "\n\nYou are answering a temporary side conversation. Use the supplied conversation context only as reference and do not claim to be the main conversation.",
            }
        )
        session.add_messages(*request.clean_context)
    elif request.context_update and request.clean_context:
        transcript = "\n\n".join(
            f"{message['role'].upper()}: {message['content']}" for message in request.clean_context
        )
        session.add_messages(
            {
                "role": "system",
                "content": "Additional full context from the user's main conversation follows. Use it as reference for the next answer:\n\n"
                + transcript,
            }
        )


def _recall_memories(state: ServerState, request: ChatRequest, session: ThreadSession) -> Recall | None:
    """Budgeted recall for this turn; memory problems must never block a conversation."""
    try:
        config = load_memory_config(state)
        service = memory_service_for_state(state)
        service.apply_due_changes()
        result = recall(
            service,
            request.content or "",
            project_id=session.project_id,
            thread_id=request.thread_id,
            token_budget=config["token_budget"],
            rule_token_budget=config["rule_token_budget"],
            embedding_model=str(config["embedding_model"] or ""),
            rerank_model=str(config["rerank_model"] or ""),
        )
        service.backend.mark_used(result.memory_ids)
        return result
    except Exception:
        logging.getLogger("vera_server.memory").exception("Memory recall failed; continuing without memories")
        return None


def _build_environment(
    state: ServerState, request: ChatRequest, target_cwd: Path, perm_cfg: dict[str, Any]
) -> LocalEnvironment:
    return LocalEnvironment(
        cwd=str(target_cwd),
        allowed_write_prefix=str(target_cwd),
        allow_external_read=perm_cfg.get("operation_scope") == "project_write_external_readonly",
        allowed_read_paths=[
            str(skill.path.parent)
            for name in request.attached_skills
            if state.skill_mgr and (skill := state.skill_mgr.get_skill(name)) is not None
        ],
    )


def _register_turn_signals(state: ServerState, request: ChatRequest) -> threading.Event:
    message_id = request.client_message_id
    pending_interrupt_at = state.pending_chat_interruptions.pop(message_id, None) if message_id else None
    state.interruption_flags[request.thread_id] = bool(
        pending_interrupt_at and time.time() - pending_interrupt_at <= 60
    )
    pause_event = threading.Event()
    pause_event.set()
    state.chat_pause_events[request.thread_id] = pause_event
    return pause_event


def prepare_turn(
    state: ServerState,
    body: dict[str, Any],
    *,
    approval_policy: ApprovalPolicy | None = None,
    control: TurnControl | None = None,
    permissions_override: dict[str, Any] | None = None,
    prompt_extender: Callable[[str, dict[str, str], ThreadSession], str] | None = None,
) -> TurnContext:
    """Validate ``body`` and build the turn's context; raises `ChatRequestError` on rejection.

    ``approval_policy`` defaults to waiting for the desktop user; ``control`` defaults to the
    shared `ServerState` signals. ``permissions_override`` replaces the saved permission settings
    (used by evaluation sandboxes so a user's `allow_all` setting never leaks into a run).
    ``prompt_extender(system_prompt, prompt_vars, session)`` may append `{{slot}}` sections: the
    active profile on desktop turns, the evaluated profile in eval runs.
    """
    request = parse_chat_request(state, body)
    if control is None:
        control = TurnControl.from_state(state, request.thread_id, _register_turn_signals(state, request))
    session, created_ephemeral = _resolve_session(state, request, body)
    is_supervisor_review, is_control_decision = _check_workflow_stage(request, session)
    target_cwd = _target_cwd(state, session)
    group_registry = (
        RegistryManager(Path(session.metadata["project_root"]))
        if session.group_id and session.metadata.get("project_root")
        else state.registry_mgr
    )
    context_settings = load_context_settings(state)
    use_memory = context_settings["memory_enabled"] and session.role == "main" and not request.ephemeral
    memory_recall = _recall_memories(state, request, session) if use_memory else None
    user_memory_context = render_recall(memory_recall) if memory_recall else ""

    # The project is the write boundary. External reads are a separate, explicit policy.
    perm_cfg = normalize_permissions_config(
        permissions_override
        if permissions_override is not None
        else state.load_json_config("permissions_config.json", {})
    )
    env = _build_environment(state, request, target_cwd, perm_cfg)
    model_profile, model, tool_call_limit = _build_model(state, request)
    tool_call_budget = {
        "count": 0,
        "limit": tool_call_limit,
        "max_attempts": perm_cfg["max_tool_attempts"],
        "failed_attempts": {},
    }
    group_tools = session.metadata.get("allowed_tools")
    if is_supervisor_review:
        # Final review must be grounded in the collected run outputs; it may not
        # invent external inspections or repeat the supervisor's dispatch role.
        group_tools = ["__supervisor_review__"]

    system_prompt, context_prompt_vars, control_response_format = build_system_prompt(
        state=state,
        session=session,
        body=body,
        model_profile=model_profile,
        context_settings=context_settings,
        target_cwd=target_cwd,
        attached_skills=request.attached_skills,
        user_memory_context=user_memory_context,
        rule_trigger=request.rule_trigger,
        ephemeral=request.ephemeral,
        is_supervisor_review=is_supervisor_review,
        is_control_decision=is_control_decision,
        workflow_control=request.workflow_control,
        workflow_context_text=request.workflow_context_text,
    )
    if prompt_extender is not None and not is_control_decision:
        system_prompt = prompt_extender(system_prompt, context_prompt_vars, session)
    if request.ephemeral:
        _seed_ephemeral_context(request, session, system_prompt, created_ephemeral)

    agent = DefaultAgent(
        model=model,
        env=env,
        session=session,
        role=session.role,
        system_template=system_prompt,
        instance_template="{{task}}",
        complete_on_empty_actions=True,
        step_limit=tool_call_limit,
    )
    agent.extra_template_vars.update(context_prompt_vars)
    agent.permission_approval_actions = perm_cfg["approval_actions"]
    agent.permission_mode = perm_cfg["default_mode"]
    agent.tool_call_budget = tool_call_budget

    return TurnContext(
        state=state,
        request=request,
        session=session,
        control=control,
        approval_policy=approval_policy or InteractiveApprovalPolicy(state.pending_approvals),
        target_cwd=target_cwd,
        group_registry=group_registry,
        context_settings=context_settings,
        env=env,
        mode=perm_cfg["default_mode"],
        approval_actions=perm_cfg["approval_actions"],
        group_tools=group_tools,
        tool_call_limit=tool_call_limit,
        tool_call_budget=tool_call_budget,
        model_profile=model_profile,
        model=model,
        agent=agent,
        system_prompt=system_prompt,
        context_prompt_vars=context_prompt_vars,
        control_response_format=control_response_format,
        forced_delegate=explicit_subagent_request(request.content),
        is_control_decision=is_control_decision,
        memory_recall=memory_recall,
    )

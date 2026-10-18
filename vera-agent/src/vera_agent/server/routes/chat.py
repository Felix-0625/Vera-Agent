"""Agent chat execution routes.

Routes:
- POST /api/chat/stream: run one user turn and stream Server-Sent Events
- POST /api/chat/confirm: answer a pending tool-approval request
- POST /api/chat/interrupt, /api/chat/pause, /api/chat/resume: control a running turn
- POST /api/chat/ephemeral/close: discard an ephemeral (side chat) session

The stream appends the user turn to the thread, calls the configured model,
executes returned tool actions under the policy in `server/permissions.py`,
and persists the conversation through `ThreadSession`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.models.utils.openai_multimodal import DEFAULT_MULTIMODAL_REGEX
from vera_agent.server.chat.actions import ActionBatchResult, run_actions
from vera_agent.server.chat.mcp_session import connect_attached_mcps
from vera_agent.server.chat.prompt import build_system_prompt, enabled_attached_skills
from vera_agent.server.chat.prompt import fill_context_placeholders as _fill_context_placeholders
from vera_agent.server.chat.request import ChatRequestError, parse_chat_request
from vera_agent.server.chat.subagents import relay_subagent
from vera_agent.server.model_profile import resolve_model_profile
from vera_agent.server.permissions import (
    normalize_permissions_config,
    permission_category,
    record_tool_result,
    requires_approval,
    reserve_tool_call,
)
from vera_agent.server.state import ServerState
from vera_agent.server.user_context import (
    load_context_settings,
    load_user_memories,
    render_user_memories,
)
from vera_agent.session.registry import RegistryManager
from vera_agent.session.thread import ThreadSession
from vera_agent.tools.user_memory_tool import FORGET_USER_MEMORY_TOOL, REMEMBER_USER_TOOL

_enabled_attached_skills = enabled_attached_skills

logger = logging.getLogger("vera_server.chat")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _explicit_subagent_request(text: str) -> str | None:
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
    if any(
        token in normalized
        for token in (
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
    ):
        return None
    # Choose the reviewer only when the named agent is a reviewer (Chinese or English wording);
    # every other explicit subagent request defaults to the researcher.
    reviewer = re.search(
        r"审查员|reviewer|review\s*(?:sub\s*agent|subagent|agent)|(?:审查|评审|代码审查)(?:子智能体|子代理|智能体)",
        normalized,
    )
    return "delegate_review" if reviewer else "delegate_research"


def _repair_tool_call_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Close interrupted tool-call turns so providers accept the next request."""
    repaired: list[dict[str, Any]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        repaired.append(message)
        index += 1
        if message.get("role") != "assistant":
            continue
        calls = message.get("tool_calls") or []
        expected = {
            str(call.get("id")): str((call.get("function") or {}).get("name") or "tool")
            for call in calls
            if call.get("id")
        }
        if not expected:
            continue
        while index < len(messages) and messages[index].get("role") == "tool":
            tool_message = messages[index]
            call_id = str(tool_message.get("tool_call_id") or "")
            if call_id in expected:
                expected.pop(call_id)
            repaired.append(tool_message)
            index += 1
        for call_id, name in expected.items():
            repaired.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": "[该工具调用在上次对话中中断，未收到执行结果。请根据当前任务重新判断是否需要调用。]",
                }
            )
    return repaired


async def chat_stream(request: Request) -> StreamingResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        parsed = parse_chat_request(state, body)
    except ChatRequestError as error:
        return error.response()
    (
        thread_id,
        content,
        model_id,
        rule_trigger,
        workflow_stage,
        workflow_control,
        workflow_context_text,
        attached_skills,
        attached_mcps,
        images,
        client_message_id,
        project_id,
        ephemeral,
        context_update,
        clean_context,
    ) = (
        parsed.thread_id,
        parsed.content,
        parsed.model_id,
        parsed.rule_trigger,
        parsed.workflow_stage,
        parsed.workflow_control,
        parsed.workflow_context_text,
        parsed.attached_skills,
        parsed.attached_mcps,
        parsed.images,
        parsed.client_message_id,
        parsed.project_id,
        parsed.ephemeral,
        parsed.context_update,
        parsed.clean_context,
    )

    pending_interrupt_at = state.pending_chat_interruptions.pop(client_message_id, None) if client_message_id else None
    state.interruption_flags[thread_id] = bool(pending_interrupt_at and time.time() - pending_interrupt_at <= 60)
    pause_event = threading.Event()
    pause_event.set()
    state.chat_pause_events[thread_id] = pause_event

    if ephemeral:
        session = state.sessions.get(thread_id)
        created_ephemeral = session is None
        if session and not session.metadata.get("ephemeral"):
            return JSONResponse({"error": "The requested side conversation is not ephemeral."}, status_code=409)
        if session is None:
            session = ThreadSession(
                thread_id=thread_id, role="side", title="临时侧边对话", metadata={"ephemeral": True}
            )
            state.sessions[thread_id] = session
    else:
        session = state.get_or_create_session(thread_id)
        created_ephemeral = False
    requested_project_id = str(project_id or session.project_id or "").strip()
    if requested_project_id:
        if session.project_id and session.project_id != requested_project_id:
            return JSONResponse({"error": "Conversation cannot be moved to a different project."}, status_code=409)
        try:
            selected_project_root = state.get_project_root(requested_project_id)
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        session.project_id = requested_project_id
        session.metadata.setdefault("project_root", str(selected_project_root))
    if body.get("group_id") and not session.group_id:
        session.group_id = body["group_id"]
        if state.graph and not ephemeral:
            state.graph.attach_session_to_group(thread_id, session.group_id)

    is_supervisor_review = workflow_stage == "supervisor_review" and session.metadata.get("isolated_run") is True
    is_control_decision = workflow_stage == "control_decision" and session.metadata.get("isolated_run") is True
    if workflow_stage == "supervisor_review" and not is_supervisor_review:
        return JSONResponse(
            {"error": "Supervisor review is only available for an isolated workflow run."}, status_code=403
        )
    if workflow_stage == "control_decision" and not is_control_decision:
        return JSONResponse(
            {"error": "Control decisions are only available to isolated workflow windows."}, status_code=403
        )
    if is_control_decision and workflow_control.get("type") != session.metadata.get("workflow_node_type"):
        return JSONResponse({"error": "The control definition does not match this workflow node."}, status_code=409)

    # Working directory: Worktree path of attached group if present, otherwise root_path
    target_cwd = Path(session.metadata.get("worktree_path") or session.metadata.get("project_root") or state.root_path)
    if session.group_id and state.graph and session.group_id in state.graph.groups:
        target_cwd = state.graph.groups[session.group_id].worktree_path
    group_registry = (
        RegistryManager(Path(session.metadata["project_root"]))
        if session.group_id and session.metadata.get("project_root")
        else state.registry_mgr
    )
    context_settings = load_context_settings(state)
    user_memories = (
        load_user_memories(state)
        if context_settings["memory_enabled"] and session.role == "main" and not ephemeral
        else []
    )
    user_memory_context = render_user_memories(user_memories)

    # The project is the write boundary. External reads are a separate, explicit policy.
    perm_cfg = normalize_permissions_config(state.load_json_config("permissions_config.json", {}))
    mode = perm_cfg["default_mode"]
    operation_scope = perm_cfg.get("operation_scope", "project_write_external_readonly")
    env = LocalEnvironment(
        cwd=str(target_cwd),
        allowed_write_prefix=str(target_cwd),
        allow_external_read=operation_scope == "project_write_external_readonly",
        allowed_read_paths=[
            str(skill.path.parent)
            for name in attached_skills
            if state.skill_mgr and (skill := state.skill_mgr.get_skill(name)) is not None
        ],
    )

    # Resolve the selected model and apply its saved runtime settings.
    try:
        model_profile = resolve_model_profile(state, model_id or None)
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    if images and model_profile["config"].get("supports_images") is False:
        return JSONResponse({"error": "The selected model is configured without image input support."}, status_code=400)
    try:
        tool_call_limit = max(1, int(model_profile["config"].get("max_tool_calls") or 15))
    except (TypeError, ValueError):
        tool_call_limit = 15
    tool_call_budget = {
        "count": 0,
        "limit": tool_call_limit,
        "max_attempts": perm_cfg["max_tool_attempts"],
        "failed_attempts": {},
    }

    model = LitellmModel(
        model_name=model_profile["name"],
        model_kwargs=model_profile["model_kwargs"],
        dynamic_tool_names=[],
        allow_empty_tool_calls=True,
        multimodal_regex=DEFAULT_MULTIMODAL_REGEX,
    )
    model.context_window = model_profile["context_window"]
    forced_delegate = _explicit_subagent_request(content)

    # Permission whitelist check
    approval_actions = perm_cfg["approval_actions"]

    group_tools = session.metadata.get("allowed_tools")
    if is_supervisor_review:
        # Final review must be grounded in the collected run outputs; it may not
        # invent external inspections or repeat the supervisor's dispatch role.
        group_tools = ["__supervisor_review__"]

    # Construct Agent
    system_prompt, context_prompt_vars, control_response_format = build_system_prompt(
        state=state,
        session=session,
        body=body,
        model_profile=model_profile,
        context_settings=context_settings,
        target_cwd=target_cwd,
        attached_skills=attached_skills,
        user_memory_context=user_memory_context,
        rule_trigger=rule_trigger,
        ephemeral=ephemeral,
        is_supervisor_review=is_supervisor_review,
        is_control_decision=is_control_decision,
        workflow_control=workflow_control,
        workflow_context_text=workflow_context_text,
    )

    if ephemeral and created_ephemeral:
        session.add_messages(
            {
                "role": "system",
                "content": system_prompt
                + "\n\nYou are answering a temporary side conversation. Use the supplied conversation context only as reference and do not claim to be the main conversation.",
            }
        )
        session.add_messages(*clean_context)
    elif ephemeral and context_update and clean_context:
        transcript = "\n\n".join(f"{message['role'].upper()}: {message['content']}" for message in clean_context)
        session.add_messages(
            {
                "role": "system",
                "content": "Additional full context from the user's main conversation follows. Use it as reference for the next answer:\n\n"
                + transcript,
            }
        )

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
    agent.permission_approval_actions = approval_actions
    agent.permission_mode = mode
    agent.tool_call_budget = tool_call_budget

    async def _chat_event_generator(mcp_tools: list[dict], mcp_dispatch: dict[str, tuple[Any, str]]):
        start_time = time.time()
        state.active_chat_threads.add(thread_id)
        state.active_chat_message_ids[thread_id] = client_message_id
        step_counter = 0
        model_failed = False
        model_error_message = ""
        pending_forced_delegate = forced_delegate
        activity_log: list[dict[str, str]] = []
        subagent_runs: list[dict[str, Any]] = []

        async def wait_if_paused() -> None:
            # Keep the stream/session alive while pausing delivery. Model tokens
            # may buffer in the worker queue; tools and the next reasoning step
            # remain gated until the user resumes.
            while thread_id in state.paused_chat_threads and not state.interruption_flags.get(thread_id, False):
                await asyncio.sleep(0.1)

        def update_activity(activity_id: str, status: str, detail: str) -> None:
            for event in activity_log:
                if event["id"] == activity_id:
                    event["status"] = status
                    event["detail"] = detail
                    break

        if not ephemeral and session.group_id and group_registry:
            group_registry.update_agent_status(session.group_id, thread_id, "running")

        # This is a transport/model status, not a claim to expose hidden reasoning.
        connection_status_id = f"status-{uuid.uuid4().hex[:8]}"
        activity_log.append({"id": connection_status_id, "kind": "status", "label": "连接模型", "status": "working"})
        yield f"event: thinking\ndata: {json.dumps({'step': 0, 'content': '正在连接模型…'}, ensure_ascii=False)}\n\n"

        # Append user turn to session
        if (
            content
            and not ephemeral
            and session.title.startswith("Thread ")
            and not any(message.get("role") == "user" for message in session.messages)
        ):
            # Clients that stream without creating the thread first still get a readable title.
            session.title = " ".join(content.split())[:22] or session.title
        if content or images:
            session.add_messages(
                {
                    "role": "user",
                    "content": content,
                    "id": client_message_id or None,
                    "extra": {
                        "rule_trigger": rule_trigger,
                        "attached_skills": attached_skills,
                        "attached_mcps": attached_mcps,
                        "images": images,
                        "timestamp": time.time(),
                    },
                }
            )

        # Explicit subagent requests are dispatched as actions immediately. The
        # model then receives the real result and writes the user-facing summary.
        if pending_forced_delegate and content and not state.interruption_flags.get(thread_id, False):
            tool_name = pending_forced_delegate
            pending_forced_delegate = None
            action_id = f"act_{uuid.uuid4().hex[:8]}"
            tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
            action = {
                "tool_name": tool_name,
                "task": content,
                "command": f"{tool_name} {content[:50]}",
                "tool_call_id": tool_call_id,
            }
            forced_action_key, _ = reserve_tool_call(tool_call_budget, action)
            synthetic_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": json.dumps({"task": content}, ensure_ascii=False)},
                    }
                ],
                "extra": {"actions": [action], "timestamp": time.time()},
            }
            session.add_messages(synthetic_message)
            tool_labels = {"delegate_research": "研究子智能体", "delegate_review": "审查子智能体"}
            activity_log.append(
                {
                    "id": action_id,
                    "kind": "tool",
                    "label": tool_labels[tool_name],
                    "detail": "启动中",
                    "status": "working",
                }
            )
            yield f"event: tool_call\ndata: {json.dumps({'action_id': action_id, 'tool_name': tool_name, 'args': action}, ensure_ascii=False)}\n\n"

            category = permission_category(action, str(target_cwd))
            needs_confirm = requires_approval(mode, category, action, approval_actions)
            group_denied = session.group_id and isinstance(group_tools, list) and tool_name not in group_tools
            if group_denied:
                approved = False
            elif needs_confirm:
                update_activity(action_id, "approval", "等待用户审批")
                yield f"event: approval_required\ndata: {json.dumps({'action_id': action_id, 'tool_name': tool_name, 'args': action, 'message': '启动子智能体需要权限确认。'}, ensure_ascii=False)}\n\n"
                approval = asyncio.get_running_loop().create_future()
                pending_key = f"{thread_id}:{action_id}"
                state.pending_approvals[pending_key] = approval
                try:
                    choice = await asyncio.wait_for(approval, timeout=300.0)
                except asyncio.TimeoutError:
                    choice = "N"
                finally:
                    state.pending_approvals.pop(pending_key, None)
                approved = choice.upper().startswith("Y")
            else:
                approved = True

            if approved:
                relay_result: dict[str, Any] = {}
                async for subagent_event in relay_subagent(
                    agent.execute_subagent_tool, action, subagent_runs, relay_result
                ):
                    yield subagent_event
                out = relay_result["output"]
            else:
                out = (
                    {
                        "output": f"[Group role denied] Tool '{tool_name}' is not allowed for this conversation window.",
                        "returncode": 1,
                        "exception_info": "GroupToolDenied",
                    }
                    if group_denied
                    else {"output": "用户未批准启动子智能体。", "returncode": 1, "exception_info": "Approval Rejected"}
                )

            if approved:
                record_tool_result(tool_call_budget, forced_action_key, out)
            session.add_messages(
                *model.format_observation_messages(synthetic_message, [out], agent.get_template_vars())
            )
            update_activity(
                action_id,
                "done" if out.get("returncode", 0) == 0 else "error",
                "已完成" if out.get("returncode", 0) == 0 else "执行失败",
            )
            yield f"event: tool_result\ndata: {json.dumps({'action_id': action_id, 'tool_name': tool_name, 'output': str(out.get('output', ''))[:5000], 'returncode': out.get('returncode', 0)}, ensure_ascii=False)}\n\n"

        streamed_response: list[str] = []
        while not state.interruption_flags.get(thread_id, False):
            streamed_response = []
            await wait_if_paused()
            if state.interruption_flags.get(thread_id, False):
                break
            step_counter += 1

            try:
                # Main conversations are summarized automatically, but are never
                # silently reborn; a rebirth is reserved for subagents or an
                # explicit grouped-workflow user action.
                from vera_agent.session.context_management import compact_session

                try:
                    compact_event = await asyncio.to_thread(
                        compact_session,
                        session,
                        model_profile["name"],
                        model_profile["model_kwargs"],
                        model_profile["context_window"],
                    )
                except Exception:
                    logger.exception("Context compaction failed for %s; retaining original transcript", thread_id)
                    compact_event = None
                    activity_log.append(
                        {
                            "id": f"compact-{uuid.uuid4().hex[:8]}",
                            "kind": "status",
                            "label": "上下文压缩失败",
                            "detail": "保留原对话继续请求；若模型窗口不足，请切换模型或减少上下文。",
                            "status": "error",
                        }
                    )
                if compact_event:
                    compact_id = f"compact-{uuid.uuid4().hex[:8]}"
                    activity_log.append(
                        {
                            "id": compact_id,
                            "kind": "status",
                            "label": "压缩上下文",
                            "detail": f"约 {compact_event['before_tokens']:,} → {compact_event['after_tokens']:,} Token（本地估算）",
                            "status": "done",
                        }
                    )
                    yield f"event: context_management\ndata: {json.dumps(compact_event, ensure_ascii=False)}\n\n"
                if is_control_decision:
                    # Repeated loop checks are independent evaluations; a prior verdict must not bias this check.
                    current_user_turn = next(
                        (message for message in reversed(session.messages) if message.get("role") == "user"), None
                    )
                    chat_history = [dict(current_user_turn)] if current_user_turn else []
                else:
                    chat_history = [
                        dict(message) for message in session.get_chat_history(prune_stale_observations=True)
                    ]
                    chat_history = _repair_tool_call_history(chat_history)
                rendered_system_prompt = _fill_context_placeholders(system_prompt, context_prompt_vars)
                chat_history.insert(0, model.format_message(role="system", content=rendered_system_prompt))
                for history_message in chat_history:
                    history_images = history_message.get("extra", {}).get("images", [])
                    if history_message.get("role") != "user" or not history_images:
                        continue
                    multimodal_content = str(history_message.get("content", ""))
                    for image in history_images:
                        image_url = image.get("data_url", "")
                        multimodal_content += (
                            "\n<MSWEA_MULTIMODAL_CONTENT><CONTENT_TYPE>image_url</CONTENT_TYPE>"
                            f"{image_url}</MSWEA_MULTIMODAL_CONTENT>"
                        )
                    history_message["content"] = model.format_message(role="user", content=multimodal_content)[
                        "content"
                    ]

                if hasattr(model, "query_stream"):
                    stream_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
                    loop = asyncio.get_running_loop()
                    generation_status_id = ""
                    generation_status_sent = False

                    def forward_stream_text(text: str) -> None:
                        pause_event.wait()
                        if state.interruption_flags.get(thread_id, False):
                            raise InterruptedError("Chat response was interrupted.")
                        loop.call_soon_threadsafe(stream_queue.put_nowait, ("text", text))

                    def stream_worker() -> None:
                        try:
                            result = model.query_stream(
                                chat_history,
                                tools=[]
                                if is_control_decision
                                else agent.get_tools()
                                + mcp_tools
                                + (
                                    [REMEMBER_USER_TOOL, FORGET_USER_MEMORY_TOOL]
                                    if context_settings["memory_enabled"]
                                    and session.role == "main"
                                    and not ephemeral
                                    and not session.group_id
                                    else []
                                ),
                                on_text=forward_stream_text,
                                **({"response_format": control_response_format} if is_control_decision else {}),
                            )
                            loop.call_soon_threadsafe(stream_queue.put_nowait, ("done", result))
                        except Exception as error:
                            loop.call_soon_threadsafe(stream_queue.put_nowait, ("error", error))

                    worker_task = asyncio.create_task(asyncio.to_thread(stream_worker))
                    while True:
                        try:
                            event_kind, event_value = await asyncio.wait_for(stream_queue.get(), timeout=2.5)
                        except asyncio.TimeoutError:
                            if state.interruption_flags.get(thread_id, False):
                                worker_task.cancel()
                                break
                            yield f"event: thinking\ndata: {json.dumps({'step': 0, 'content': '模型处理中，等待首个响应…'}, ensure_ascii=False)}\n\n"
                            continue
                        await wait_if_paused()
                        if state.interruption_flags.get(thread_id, False):
                            break
                        if event_kind == "text":
                            streamed_response.append(str(event_value))
                            if connection_status_id:
                                update_activity(connection_status_id, "done", "已连接")
                                connection_status_id = ""
                            if not generation_status_sent:
                                generation_status_id = f"status-{uuid.uuid4().hex[:8]}"
                                activity_log.append(
                                    {
                                        "id": generation_status_id,
                                        "kind": "status",
                                        "label": "生成回答",
                                        "status": "working",
                                    }
                                )
                                generation_status_sent = True
                                yield f"event: thinking\ndata: {json.dumps({'step': 1, 'content': '正在生成回答…'}, ensure_ascii=False)}\n\n"
                            yield f"event: text_chunk\ndata: {json.dumps({'content': event_value}, ensure_ascii=False)}\n\n"
                        elif event_kind == "error":
                            await worker_task
                            raise event_value
                        else:
                            model_msg = event_value
                            await worker_task
                            if generation_status_id:
                                update_activity(generation_status_id, "done", "已接收模型输出")
                            break
                else:
                    # Preserve compatibility with non-LiteLLM model adapters. These
                    # adapters currently expose only a complete-response query API.
                    model_msg = await asyncio.to_thread(
                        model.query,
                        chat_history,
                        tools=[]
                        if is_control_decision
                        else agent.get_tools()
                        + mcp_tools
                        + (
                            [REMEMBER_USER_TOOL, FORGET_USER_MEMORY_TOOL]
                            if context_settings["memory_enabled"]
                            and session.role == "main"
                            and not ephemeral
                            and not session.group_id
                            else []
                        ),
                        **({"response_format": control_response_format} if is_control_decision else {}),
                    )
                    response_content = model_msg.get("content", "")
                    if response_content:
                        yield f"event: text_chunk\ndata: {json.dumps({'content': response_content}, ensure_ascii=False)}\n\n"
                if state.interruption_flags.get(thread_id, False):
                    break
                session.add_messages(model_msg)
            except Exception as e:
                if state.interruption_flags.get(thread_id, False):
                    break
                model_error_message = f"Model inference error: {e}"
                yield f"event: text_chunk\ndata: {json.dumps({'content': model_error_message}, ensure_ascii=False)}\n\n"
                model_failed = True
                break

            actions = model_msg.get("extra", {}).get("actions", [])
            response_content = model_msg.get("content", "")

            if not actions:
                break

            # Execute actions
            outputs = []
            tool_limit_reached = False
            action_batch = ActionBatchResult()
            async for action_event in run_actions(
                actions,
                action_batch,
                state=state,
                session=session,
                agent=agent,
                env=env,
                thread_id=thread_id,
                target_cwd=target_cwd,
                mode=mode,
                approval_actions=approval_actions,
                group_tools=group_tools,
                tool_call_budget=tool_call_budget,
                mcp_dispatch=mcp_dispatch,
                activity_log=activity_log,
                subagent_runs=subagent_runs,
                update_activity=update_activity,
                wait_if_paused=wait_if_paused,
            ):
                yield action_event
            outputs = action_batch.outputs
            tool_limit_reached = action_batch.tool_limit_reached

            obs_msgs = model.format_observation_messages(model_msg, outputs, agent.get_template_vars())
            session.add_messages(*obs_msgs)

            if tool_limit_reached:
                break
            if step_counter >= tool_call_limit:
                break

        duration = round(time.time() - start_time, 2)
        exit_status = (
            "error" if model_failed else ("interrupted" if state.interruption_flags.get(thread_id) else "finish")
        )
        if model_failed:
            session.add_messages(
                {
                    "role": "assistant",
                    "content": model_error_message,
                    "extra": {"timestamp": start_time, "error": True},
                }
            )
        if exit_status == "interrupted":
            last_assistant = next(
                (
                    message
                    for message in reversed(session.messages)
                    if message.get("role") == "assistant"
                    and float((message.get("extra") or {}).get("timestamp") or 0) >= start_time
                ),
                None,
            )
            last_assistant_actions = ((last_assistant or {}).get("extra") or {}).get("actions", [])
            if last_assistant is None or last_assistant_actions:
                partial = "".join(streamed_response).strip()
                interrupted_content = (
                    f"[本轮已中断，以下为已生成内容]\n{partial}" if partial else "（本轮已中断，尚未生成完整回答。）"
                )
                session.add_messages(
                    {
                        "role": "assistant",
                        "content": interrupted_content,
                        "extra": {"timestamp": start_time, "interrupted": True},
                    }
                )
        for event in activity_log:
            if event["status"] == "working":
                event["status"] = "done" if event["kind"] == "status" else "error"
                event["detail"] = (
                    "已中断" if exit_status == "interrupted" else ("" if event["kind"] == "status" else "未完成")
                )

        # Automatic compaction may replace the history list and move the original
        # turn index; timestamp matching keeps activity attached to this response.
        for message in reversed(session.messages):
            message_time = float((message.get("extra") or {}).get("timestamp") or 0)
            if message.get("role") == "assistant" and message_time >= start_time:
                extra = dict(message.get("extra") or {})
                extra["activity"] = activity_log
                if subagent_runs:
                    extra["subagents"] = subagent_runs
                extra["duration"] = duration
                message["extra"] = extra
                break

        # Persist normal sessions; ephemeral side conversations stay in memory only.
        if not ephemeral:
            session.save(state.get_session_file(session))
        if not ephemeral and session.group_id and group_registry:
            group_registry.update_agent_status(session.group_id, thread_id, "idle")

        finish_payload = {
            "duration": duration,
            "steps": step_counter,
            "cost": round(agent.cost, 4),
            "total_cost": round(session.cost, 4),
            "exit_status": exit_status,
        }
        state.active_chat_threads.discard(thread_id)
        if state.active_chat_message_ids.get(thread_id) == client_message_id:
            state.active_chat_message_ids.pop(thread_id, None)
            state.interruption_flags[thread_id] = False
        state.paused_chat_threads.discard(thread_id)
        state.chat_pause_events.pop(thread_id, None)
        yield f"event: finish\ndata: {json.dumps(finish_payload, ensure_ascii=False)}\n\n"
        if ephemeral and session.metadata.get("closed"):
            state.sessions.pop(thread_id, None)
            state.interruption_flags.pop(thread_id, None)

    async def sse_event_generator():
        async with AsyncExitStack() as stack:
            mcp_tools: list[dict] = []
            mcp_dispatch: dict[str, tuple[Any, str]] = {}
            async for notice in connect_attached_mcps(stack, state, attached_mcps, target_cwd, mcp_tools, mcp_dispatch):
                yield notice
            model.config.dynamic_tool_names = list(mcp_dispatch)
            if context_settings["memory_enabled"] and session.role == "main" and not ephemeral and not session.group_id:
                model.config.dynamic_tool_names.extend(["remember_user", "forget_user_memory"])
            async for event in _chat_event_generator(mcp_tools, mcp_dispatch):
                yield event

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def chat_confirm(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    thread_id = body.get("thread_id")
    action_id = body.get("action_id")
    choice = body.get("choice", "Y")

    if not thread_id or not action_id:
        return JSONResponse({"error": "thread_id and action_id required"}, status_code=400)

    key = f"{thread_id}:{action_id}"
    if key in state.pending_approvals and not state.pending_approvals[key].done():
        state.pending_approvals[key].set_result(choice)
        return JSONResponse({"status": "ok", "choice": choice})

    return JSONResponse({"error": "No pending approval for this action"}, status_code=404)


async def chat_interrupt(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    thread_id = body.get("thread_id")
    if not thread_id:
        return JSONResponse({"error": "thread_id required"}, status_code=400)

    client_message_id = str(body.get("client_message_id") or "")
    if client_message_id and state.active_chat_message_ids.get(thread_id) != client_message_id:
        cutoff = time.time() - 60
        state.pending_chat_interruptions = {
            message_id: requested_at
            for message_id, requested_at in state.pending_chat_interruptions.items()
            if requested_at >= cutoff
        }
        state.pending_chat_interruptions[client_message_id] = time.time()
        return JSONResponse({"status": "ok", "interrupted": False})

    state.interruption_flags[thread_id] = True
    state.paused_chat_threads.discard(thread_id)
    pause_event = state.chat_pause_events.get(thread_id)
    if pause_event:
        pause_event.set()
    for k, fut in list(state.pending_approvals.items()):
        if k.startswith(f"{thread_id}:") and not fut.done():
            fut.set_result("N")

    return JSONResponse({"status": "ok", "interrupted": True})


async def chat_pause(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    thread_id = str(body.get("thread_id") or "")
    if not thread_id:
        return JSONResponse({"error": "thread_id required"}, status_code=400)
    state.paused_chat_threads.add(thread_id)
    pause_event = state.chat_pause_events.get(thread_id)
    if pause_event:
        pause_event.clear()
    return JSONResponse({"status": "ok", "paused": True})


async def chat_resume(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    thread_id = str(body.get("thread_id") or "")
    if not thread_id:
        return JSONResponse({"error": "thread_id required"}, status_code=400)
    state.paused_chat_threads.discard(thread_id)
    pause_event = state.chat_pause_events.get(thread_id)
    if pause_event:
        pause_event.set()
    return JSONResponse({"status": "ok", "resumed": True})


async def close_ephemeral_chat(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    thread_id = str(body.get("thread_id") or "")
    if not thread_id.startswith("side_"):
        return JSONResponse({"error": "Only ephemeral side conversations can be closed here."}, status_code=400)
    session = state.sessions.get(thread_id)
    if session and not session.metadata.get("ephemeral"):
        return JSONResponse({"error": "The requested conversation is not ephemeral."}, status_code=409)
    if session:
        session.metadata["closed"] = True
    state.sessions.pop(thread_id, None)
    state.interruption_flags[thread_id] = True
    for key, future in list(state.pending_approvals.items()):
        if key.startswith(f"{thread_id}:"):
            if not future.done():
                future.set_result("N")
            state.pending_approvals.pop(key, None)
    return JSONResponse({"status": "ok", "closed_thread_id": thread_id})


chat_routes = [
    Route("/api/chat/stream", chat_stream, methods=["POST"]),
    Route("/api/chat/confirm", chat_confirm, methods=["POST"]),
    Route("/api/chat/interrupt", chat_interrupt, methods=["POST"]),
    Route("/api/chat/pause", chat_pause, methods=["POST"]),
    Route("/api/chat/resume", chat_resume, methods=["POST"]),
    Route("/api/chat/ephemeral/close", close_ephemeral_chat, methods=["POST"]),
]

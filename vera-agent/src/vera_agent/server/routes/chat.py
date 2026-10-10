"""Module 1: Agent Execution & Streaming Chat (SSE, HITL approval, interrupt)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.models.utils.openai_multimodal import DEFAULT_MULTIMODAL_REGEX
from vera_agent.server.model_profile import resolve_model_profile
from vera_agent.server.state import ServerState
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.chat")


def _permission_categories(action: dict, project_root: Path) -> set[str]:
    """Map runtime tool names to the permission categories shown in settings."""
    tool_name = action.get("tool_name")
    if not tool_name and "command" in action:
        return {"terminal"}
    if tool_name in {"read", "symbol_search", "check_syntax"}:
        return {"read"}
    if tool_name == "edit":
        return {"edit"}
    if tool_name == "write":
        target = Path(str(action.get("path", "")))
        if not target.is_absolute():
            target = project_root / target
        return {"edit" if target.exists() else "create"}
    if tool_name in {"web_search", "fetch_web_page", "delegate_research", "delegate_review"}:
        return {"mcp"}
    # Unknown runtime tools keep their own name so they fail closed until added
    # to the permission configuration.
    return {str(tool_name or "unknown")}


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _explicit_subagent_request(text: str) -> str | None:
    """Return the delegate when the user explicitly asks to run a subagent."""
    normalized = text.lower()
    agent_mention = r"(?:sub\s*agent|subagent|子智能体|子代理|研究员|审查员|reviewer)"
    action = r"(?:创建|启动|调用|委派|派出|运行|create|start|invoke|run|让.{0,4}执行)"
    if not (re.search(rf"{action}.{{0,16}}{agent_mention}", normalized) or re.search(rf"{agent_mention}.{{0,16}}{action}", normalized)):
        return None
    if any(token in normalized for token in ("不要创建", "不要启动", "不要调用", "不需要创建", "不用创建", "don't create", "do not create", "don't invoke", "do not invoke")):
        return None
    reviewer = re.search(r"(?:审查员|reviewer).{0,12}(?:创建|启动|调用|委派|派出|运行)|(?:创建|启动|调用|委派|派出|运行).{0,12}(?:审查员|reviewer)", normalized)
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
            repaired.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": "[该工具调用在上次对话中中断，未收到执行结果。请根据当前任务重新判断是否需要调用。]",
            })
    return repaired


async def chat_stream(request: Request) -> StreamingResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"
    content = body.get("content", "").strip()
    model_id = body.get("model_id")
    mode = body.get("mode", "confirm")  # "confirm" | "yolo" | "human"
    rule_trigger = body.get("rule_trigger")  # "goal" | "plan" | None
    attached_skills = body.get("attached_skills") or []
    attached_mcps = body.get("attached_mcps") or []
    images = body.get("images") or []
    client_message_id = str(body.get("client_message_id") or "")
    project_id = body.get("project_id")
    ephemeral = body.get("ephemeral") is True
    context_update = body.get("context_update") is True
    context_messages = body.get("context_messages") or []

    if ephemeral and not thread_id.startswith("side_"):
        return JSONResponse({"error": "Ephemeral chat IDs must use the side_ prefix."}, status_code=400)
    if not isinstance(context_messages, list) or len(context_messages) > 100:
        return JSONResponse({"error": "Context must contain at most 100 messages."}, status_code=400)
    clean_context: list[dict[str, str]] = []
    context_size = 0
    for message in context_messages:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"} or not isinstance(message.get("content"), str):
            return JSONResponse({"error": "Context messages must have user or assistant roles and text content."}, status_code=400)
        context_content = message["content"][:30_000]
        context_size += len(context_content)
        if context_size > 250_000:
            return JSONResponse({"error": "Context is too large."}, status_code=413)
        clean_context.append({"role": message["role"], "content": context_content})

    if not isinstance(images, list) or len(images) > 4:
        return JSONResponse({"error": "At most four images can be attached to a message."}, status_code=400)
    for image in images:
        if not isinstance(image, dict) or not str(image.get("data_url", "")).startswith("data:image/"):
            return JSONResponse({"error": "Image attachments must be image data URLs."}, status_code=400)
        if len(str(image["data_url"])) > 11_500_000:
            return JSONResponse({"error": "Each image must be 8 MB or smaller."}, status_code=400)

    state.interruption_flags[thread_id] = False
    pause_event = threading.Event()
    pause_event.set()
    state.chat_pause_events[thread_id] = pause_event

    if ephemeral:
        session = state.sessions.get(thread_id)
        created_ephemeral = session is None
        if session and not session.metadata.get("ephemeral"):
            return JSONResponse({"error": "The requested side conversation is not ephemeral."}, status_code=409)
        if session is None:
            session = ThreadSession(thread_id=thread_id, role="side", title="临时侧边对话", metadata={"ephemeral": True})
            state.sessions[thread_id] = session
    else:
        session = state.get_or_create_session(thread_id)
        created_ephemeral = False
    if project_id:
        session.project_id = project_id
    if body.get("group_id") and not session.group_id:
        session.group_id = body["group_id"]
        if state.graph and not ephemeral:
            state.graph.attach_session_to_group(thread_id, session.group_id)

    # Working directory: Worktree path of attached group if present, otherwise root_path
    target_cwd = state.root_path
    if session.group_id and state.graph and session.group_id in state.graph.groups:
        target_cwd = state.graph.groups[session.group_id].worktree_path

    # The project is the write boundary. External reads are a separate, explicit policy.
    perm_cfg = state.load_json_config("permissions_config.json", {
        "default_mode": "confirm",
        "whitelist_actions": ["read", "create", "edit", "delete", "terminal", "mcp"],
        "operation_scope": "project_write_external_readonly",
    })
    operation_scope = perm_cfg.get("operation_scope", "project_write_external_readonly")
    env = LocalEnvironment(
        cwd=str(target_cwd),
        allowed_write_prefix=str(target_cwd),
        allow_external_read=operation_scope == "project_write_external_readonly",
    )

    # Resolve the selected model and apply its saved runtime settings.
    model_profile = resolve_model_profile(state, model_id or None)

    model = LitellmModel(
        model_name=model_profile["name"],
        model_kwargs=model_profile["model_kwargs"],
        allow_empty_tool_calls=True,
        multimodal_regex=DEFAULT_MULTIMODAL_REGEX,
    )
    model.context_window = model_profile["context_window"]
    forced_delegate = _explicit_subagent_request(content)

    # Permission whitelist check
    whitelist = perm_cfg.get("whitelist_actions", ["read", "create", "edit", "delete", "terminal", "mcp"])

    # Construct Agent
    system_prompt = (
        "You are an expert AI software engineer operating in an isolated GitFlow environment. "
        "Use write tool to create new files, edit tool to update existing files, read to inspect, and bash to test. "
        "Direct all diagnostic logs to stderr and keep answers concise. "
        "When the user explicitly asks you to create, start, or invoke a subagent, call the matching delegate tool immediately; "
        "never say it is created or running until that tool has actually run."
    )
    if rule_trigger == "plan":
        system_prompt += "\n[PLAN MODE TRIGGERED]: Outline architecture and proposed file changes explicitly before touching code."
    elif rule_trigger == "goal":
        system_prompt += "\n[GOAL MODE TRIGGERED]: Execute autonomously until all acceptance criteria and tests pass."

    if state.skill_mgr:
        for sk_name in attached_skills:
            sk_text = state.skill_mgr.render_skill_instruction(sk_name)
            if sk_text:
                system_prompt += f"\n\n{sk_text}"

    if ephemeral and created_ephemeral:
        session.add_messages({"role": "system", "content": system_prompt + "\n\nYou are answering a temporary side conversation. Use the supplied conversation context only as reference and do not claim to be the main conversation."})
        session.add_messages(*clean_context)
    elif ephemeral and context_update and clean_context:
        transcript = "\n\n".join(f"{message['role'].upper()}: {message['content']}" for message in clean_context)
        session.add_messages({"role": "system", "content": "Additional full context from the user's main conversation follows. Use it as reference for the next answer:\n\n" + transcript})

    agent = DefaultAgent(
        model=model,
        env=env,
        session=session,
        role=session.role,
        system_template=system_prompt,
        instance_template="{{task}}",
        complete_on_empty_actions=True,
        step_limit=int(model_profile["config"].get("max_tool_calls") or 15),
    )
    agent.permission_whitelist = whitelist
    agent.permission_mode = mode

    async def sse_event_generator():
        start_time = time.time()
        state.active_chat_threads.add(thread_id)
        step_counter = 0
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

        if not ephemeral and session.group_id and state.registry_mgr:
            state.registry_mgr.update_agent_status(session.group_id, thread_id, "running")

        # This is a transport/model status, not a claim to expose hidden reasoning.
        connection_status_id = f"status-{uuid.uuid4().hex[:8]}"
        activity_log.append({"id": connection_status_id, "kind": "status", "label": "连接模型", "status": "working"})
        yield f"event: thinking\ndata: {json.dumps({'step': 0, 'content': '正在连接模型…'}, ensure_ascii=False)}\n\n"

        # Append user turn to session
        if content or images:
            session.add_messages({
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
            })

        # Explicit subagent requests are dispatched as actions immediately. The
        # model then receives the real result and writes the user-facing summary.
        if pending_forced_delegate and content:
            tool_name = pending_forced_delegate
            pending_forced_delegate = None
            action_id = f"act_{uuid.uuid4().hex[:8]}"
            tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
            action = {"tool_name": tool_name, "task": content, "command": f"{tool_name} {content[:50]}", "tool_call_id": tool_call_id}
            synthetic_message = {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": tool_name, "arguments": json.dumps({"task": content}, ensure_ascii=False)}}],
                "extra": {"actions": [action], "timestamp": time.time()},
            }
            session.add_messages(synthetic_message)
            tool_labels = {"delegate_research": "研究子智能体", "delegate_review": "审查子智能体"}
            activity_log.append({"id": action_id, "kind": "tool", "label": tool_labels[tool_name], "detail": "启动中", "status": "working"})
            yield f"event: tool_call\ndata: {json.dumps({'action_id': action_id, 'tool_name': tool_name, 'args': action}, ensure_ascii=False)}\n\n"

            needs_confirm = mode == "human" or (mode == "confirm" and "mcp" not in whitelist)
            if needs_confirm:
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
                progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
                loop = asyncio.get_running_loop()

                def on_subagent_progress(run: dict[str, Any]) -> None:
                    loop.call_soon_threadsafe(progress_queue.put_nowait, run)

                child_task = asyncio.create_task(asyncio.to_thread(agent.execute_subagent_tool, action, on_subagent_progress))
                while not child_task.done():
                    try:
                        run = await asyncio.wait_for(progress_queue.get(), timeout=0.15)
                    except asyncio.TimeoutError:
                        continue
                    existing_index = next((i for i, item in enumerate(subagent_runs) if item.get("id") == run.get("id")), None)
                    if existing_index is None:
                        subagent_runs.append(run)
                    else:
                        subagent_runs[existing_index] = run
                    yield f"event: subagent\ndata: {json.dumps(run, ensure_ascii=False)}\n\n"
                out = await child_task
                while not progress_queue.empty():
                    run = progress_queue.get_nowait()
                    existing_index = next((i for i, item in enumerate(subagent_runs) if item.get("id") == run.get("id")), None)
                    if existing_index is None:
                        subagent_runs.append(run)
                    else:
                        subagent_runs[existing_index] = run
                    yield f"event: subagent\ndata: {json.dumps(run, ensure_ascii=False)}\n\n"
            else:
                out = {"output": "用户未批准启动子智能体。", "returncode": 1, "exception_info": "Approval Rejected"}

            session.add_messages(*model.format_observation_messages(synthetic_message, [out], agent.get_template_vars()))
            update_activity(action_id, "done" if out.get("returncode", 0) == 0 else "error", "已完成" if out.get("returncode", 0) == 0 else "执行失败")
            yield f"event: tool_result\ndata: {json.dumps({'action_id': action_id, 'tool_name': tool_name, 'output': str(out.get('output', ''))[:5000], 'returncode': out.get('returncode', 0)}, ensure_ascii=False)}\n\n"

        while not state.interruption_flags.get(thread_id, False):
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
                except Exception as compact_error:
                    logger.exception("Context compaction failed for %s; retaining original transcript", thread_id)
                    compact_event = None
                    activity_log.append({"id": f"compact-{uuid.uuid4().hex[:8]}", "kind": "status", "label": "上下文压缩失败", "detail": "保留原对话继续请求；若模型窗口不足，请切换模型或减少上下文。", "status": "error"})
                if compact_event:
                    compact_id = f"compact-{uuid.uuid4().hex[:8]}"
                    activity_log.append({"id": compact_id, "kind": "status", "label": "压缩上下文", "detail": f"{compact_event['before_tokens']:,} → {compact_event['after_tokens']:,} Token", "status": "done"})
                    yield f"event: context_management\ndata: {json.dumps(compact_event, ensure_ascii=False)}\n\n"
                chat_history = [dict(message) for message in session.get_chat_history(prune_stale_observations=True)]
                chat_history = _repair_tool_call_history(chat_history)
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
                    history_message["content"] = model.format_message(
                        role="user", content=multimodal_content
                    )["content"]

                if hasattr(model, "query_stream"):
                    stream_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
                    loop = asyncio.get_running_loop()
                    generation_status_id = ""
                    generation_status_sent = False

                    def stream_worker() -> None:
                        try:
                            result = model.query_stream(
                                chat_history,
                                tools=agent.get_tools(),
                                on_text=lambda text: (
                                    pause_event.wait(),
                                    loop.call_soon_threadsafe(stream_queue.put_nowait, ("text", text)),
                                ),
                            )
                            loop.call_soon_threadsafe(stream_queue.put_nowait, ("done", result))
                        except Exception as error:
                            loop.call_soon_threadsafe(stream_queue.put_nowait, ("error", error))

                    worker_task = asyncio.create_task(asyncio.to_thread(stream_worker))
                    while True:
                        try:
                            event_kind, event_value = await asyncio.wait_for(stream_queue.get(), timeout=2.5)
                        except asyncio.TimeoutError:
                            yield f"event: thinking\ndata: {json.dumps({'step': 0, 'content': '模型处理中，等待首个响应…'}, ensure_ascii=False)}\n\n"
                            continue
                        await wait_if_paused()
                        if state.interruption_flags.get(thread_id, False):
                            break
                        if event_kind == "text":
                            if connection_status_id:
                                update_activity(connection_status_id, "done", "已连接")
                                connection_status_id = ""
                            if not generation_status_sent:
                                generation_status_id = f"status-{uuid.uuid4().hex[:8]}"
                                activity_log.append({"id": generation_status_id, "kind": "status", "label": "生成回答", "status": "working"})
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
                    model_msg = await asyncio.to_thread(model.query, chat_history, tools=agent.get_tools())
                    response_content = model_msg.get("content", "")
                    if response_content:
                        yield f"event: text_chunk\ndata: {json.dumps({'content': response_content}, ensure_ascii=False)}\n\n"
                session.add_messages(model_msg)
            except Exception as e:
                yield f"event: text_chunk\ndata: {json.dumps({'content': f'Model inference error: {e}'}, ensure_ascii=False)}\n\n"
                break

            actions = model_msg.get("extra", {}).get("actions", [])
            response_content = model_msg.get("content", "")

            if not actions:
                break

            # Execute actions
            outputs = []
            for act in actions:
                await wait_if_paused()
                if state.interruption_flags.get(thread_id, False):
                    break

                act_id = f"act_{uuid.uuid4().hex[:8]}"
                tool_name = act.get("tool_name", "")
                tool_labels = {"read": "读取文件", "write": "写入文件", "edit": "修改文件", "web_search": "网页搜索", "fetch_web_page": "读取网页", "delegate_research": "研究任务", "delegate_review": "审查任务"}
                activity_log.append({"id": act_id, "kind": "tool", "label": tool_labels.get(tool_name, "终端命令" if not tool_name else tool_name), "detail": "执行中", "status": "working"})

                yield f"event: tool_call\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act}, ensure_ascii=False)}\n\n"

                # Confirmation Gating
                categories = _permission_categories(act, state.root_path)
                needs_confirm = (mode == "human") or (mode == "confirm" and not categories.issubset(whitelist))
                if needs_confirm:
                    update_activity(act_id, "approval", "等待用户审批")
                    yield f"event: approval_required\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act, 'message': f'High-risk operation ({tool_name}) requires approval.'}, ensure_ascii=False)}\n\n"

                    fut = asyncio.get_running_loop().create_future()
                    pending_key = f"{thread_id}:{act_id}"
                    state.pending_approvals[pending_key] = fut

                    try:
                        choice = await asyncio.wait_for(fut, timeout=300.0)
                    except asyncio.TimeoutError:
                        choice = "N"
                    finally:
                        state.pending_approvals.pop(pending_key, None)

                    if choice.upper().startswith("N"):
                        out = {
                            "output": "[Approval Rejected] Operation rejected by user.",
                            "returncode": 1,
                            "exception_info": "Approval Rejected",
                        }
                        outputs.append(out)
                        update_activity(act_id, "error", "用户拒绝")
                        yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                        continue
                    elif choice.upper().startswith("O:"):
                        feedback = choice[2:].strip()
                        out = {
                            "output": f"[User Override/Correction]: {feedback}",
                            "returncode": 1,
                            "exception_info": "",
                        }
                        outputs.append(out)
                        update_activity(act_id, "done", "已提交修改意见")
                        yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                        continue

                # Execute tool in environment
                try:
                    if tool_name in {"delegate_research", "delegate_review"}:
                        progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
                        loop = asyncio.get_running_loop()

                        def on_subagent_progress(run: dict[str, Any]) -> None:
                            loop.call_soon_threadsafe(progress_queue.put_nowait, run)

                        child_task = asyncio.create_task(
                            asyncio.to_thread(agent.execute_subagent_tool, act, on_subagent_progress)
                        )
                        while not child_task.done():
                            try:
                                run = await asyncio.wait_for(progress_queue.get(), timeout=0.15)
                            except asyncio.TimeoutError:
                                continue
                            existing_index = next((i for i, item in enumerate(subagent_runs) if item.get("id") == run.get("id")), None)
                            if existing_index is None:
                                subagent_runs.append(run)
                            else:
                                subagent_runs[existing_index] = run
                            yield f"event: subagent\ndata: {json.dumps(run, ensure_ascii=False)}\n\n"
                        out = await child_task
                        while not progress_queue.empty():
                            run = progress_queue.get_nowait()
                            existing_index = next((i for i, item in enumerate(subagent_runs) if item.get("id") == run.get("id")), None)
                            if existing_index is None:
                                subagent_runs.append(run)
                            else:
                                subagent_runs[existing_index] = run
                            yield f"event: subagent\ndata: {json.dumps(run, ensure_ascii=False)}\n\n"
                    else:
                        # Keep the ASGI loop responsive so pause/interrupt and
                        # other conversation controls remain actionable while a
                        # synchronous environment tool is running.
                        out = await asyncio.to_thread(env.execute, act)
                    if "exception_info" not in out:
                        out["exception_info"] = ""
                except Exception as e:
                    out = {"output": f"Execution error: {e}", "returncode": -1, "exception_info": str(e)}

                outputs.append(out)
                clean_output = str(out.get("output", ""))[:5000]
                update_activity(act_id, "done" if out.get("returncode", 0) == 0 else "error", "已完成" if out.get("returncode", 0) == 0 else "执行失败")
                yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': clean_output, 'returncode': out.get('returncode', 0)}, ensure_ascii=False)}\n\n"

            obs_msgs = model.format_observation_messages(model_msg, outputs, agent.get_template_vars())
            session.add_messages(*obs_msgs)

            if step_counter >= 15:
                break

        duration = round(time.time() - start_time, 2)
        exit_status = "interrupted" if state.interruption_flags.get(thread_id) else "finish"
        for event in activity_log:
            if event["status"] == "working":
                event["status"] = "done" if event["kind"] == "status" else "error"
                event["detail"] = "已中断" if exit_status == "interrupted" else ("" if event["kind"] == "status" else "未完成")

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
            session.save(state.get_sessions_dir() / f"{thread_id}.json")
        if not ephemeral and session.group_id and state.registry_mgr:
            state.registry_mgr.update_agent_status(session.group_id, thread_id, "idle")

        finish_payload = {
            "duration": duration,
            "steps": step_counter,
            "cost": round(agent.cost, 4),
            "total_cost": round(session.cost, 4),
            "exit_status": exit_status,
        }
        state.active_chat_threads.discard(thread_id)
        state.paused_chat_threads.discard(thread_id)
        state.chat_pause_events.pop(thread_id, None)
        yield f"event: finish\ndata: {json.dumps(finish_payload, ensure_ascii=False)}\n\n"
        if ephemeral and session.metadata.get("closed"):
            state.sessions.pop(thread_id, None)
            state.interruption_flags.pop(thread_id, None)

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

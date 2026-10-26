"""Run one chat turn and yield its Server-Sent Event strings.

`run_turn(ctx)` is the single execution path for a user turn: it appends the user message,
dispatches an explicitly requested subagent, alternates model calls and tool actions until the
model stops, the tool budget runs out or the turn is interrupted, then persists the session.

The HTTP route (`server/routes/chat.py`) only builds the `TurnContext` and forwards the events;
the eval runner (`evals/runner.py`) drives the same function headlessly with its own
`ApprovalPolicy` and `TurnControl`. When ``ctx.tracer`` is set, every model call and tool action
is recorded as a span and the trace is finished after the `finish` event's data is known.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from vera_agent.server.chat.actions import (
    ActionBatchResult,
    approval_required_event,
    group_denied_output,
    run_actions,
    tool_result_event,
)
from vera_agent.server.chat.model_step import model_step
from vera_agent.server.chat.progress import TurnProgress, sse
from vera_agent.server.chat.subagents import relay_subagent
from vera_agent.server.chat.turn_setup import TurnContext
from vera_agent.server.permissions import permission_category, record_tool_result, requires_approval, reserve_tool_call


def _append_user_message(ctx: TurnContext) -> None:
    request, session = ctx.request, ctx.session
    content = request.content
    if (
        content
        and not request.ephemeral
        and session.title.startswith("Thread ")
        and not any(message.get("role") == "user" for message in session.messages)
    ):
        # Clients that stream without creating the thread first still get a readable title.
        session.title = " ".join(content.split())[:22] or session.title
    if content or request.images:
        session.add_messages(
            {
                "role": "user",
                "content": content,
                "id": request.client_message_id or None,
                "extra": {
                    "rule_trigger": request.rule_trigger,
                    "attached_skills": request.attached_skills,
                    "attached_mcps": request.attached_mcps,
                    "images": request.images,
                    "timestamp": time.time(),
                },
            }
        )


async def _dispatch_forced_delegate(ctx: TurnContext, progress: TurnProgress) -> AsyncIterator[str]:
    """Run an explicitly requested subagent; the model then summarizes its real result."""
    tool_name, content = ctx.forced_delegate, ctx.request.content
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
    action = {
        "tool_name": tool_name,
        "task": content,
        "command": f"{tool_name} {content[:50]}",
        "tool_call_id": tool_call_id,
    }
    forced_action_key, _ = reserve_tool_call(ctx.tool_call_budget, action)
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
    ctx.session.add_messages(synthetic_message)
    label = {"delegate_research": "研究子智能体", "delegate_review": "审查子智能体"}[tool_name]
    progress.activity_log.append(
        {"id": action_id, "kind": "tool", "label": label, "detail": "启动中", "status": "working"}
    )
    yield sse("tool_call", {"action_id": action_id, "tool_name": tool_name, "args": action})

    category = permission_category(action, str(ctx.target_cwd))
    if ctx.tracer:
        ctx.tracer.tool_started(action_id, tool_name, action, category)
    group_denied = ctx.session.group_id and isinstance(ctx.group_tools, list) and tool_name not in ctx.group_tools
    if group_denied:
        approved = False
    elif requires_approval(ctx.mode, category, action, ctx.approval_actions):
        progress.update_activity(action_id, "approval", "等待用户审批")
        yield approval_required_event(action_id, tool_name, action, "启动子智能体需要权限确认。")
        choice = await ctx.approval_policy.decide(
            thread_id=ctx.thread_id, action_id=action_id, action=action, category=category
        )
        if ctx.tracer:
            ctx.tracer.tool_approval(action_id, choice)
        approved = choice.upper().startswith("Y")
    else:
        approved = True

    if approved:
        relay_result: dict[str, Any] = {}
        async for subagent_event in relay_subagent(
            ctx.agent.execute_subagent_tool, action, progress.subagent_runs, relay_result
        ):
            yield subagent_event
        out = relay_result["output"]
        record_tool_result(ctx.tool_call_budget, forced_action_key, out)
    elif group_denied:
        out = group_denied_output(tool_name)
    else:
        out = {"output": "用户未批准启动子智能体。", "returncode": 1, "exception_info": "Approval Rejected"}
    ctx.session.add_messages(
        *ctx.model.format_observation_messages(synthetic_message, [out], ctx.agent.get_template_vars())
    )
    succeeded = out.get("returncode", 0) == 0
    progress.update_activity(action_id, "done" if succeeded else "error", "已完成" if succeeded else "执行失败")
    if ctx.tracer:
        ctx.tracer.tool_finished(action_id, out)
    yield tool_result_event(action_id, tool_name, str(out.get("output", ""))[:5000], out.get("returncode", 0))


async def _action_step(ctx: TurnContext, progress: TurnProgress, actions: list[dict]) -> AsyncIterator[str]:
    """Execute the model's actions and record their observations; sets ``progress.tool_limit_reached``."""
    batch = ActionBatchResult()
    async for event in run_actions(
        actions,
        batch,
        state=ctx.state,
        session=ctx.session,
        agent=ctx.agent,
        env=ctx.env,
        thread_id=ctx.thread_id,
        target_cwd=ctx.target_cwd,
        mode=ctx.mode,
        approval_actions=ctx.approval_actions,
        group_tools=ctx.group_tools,
        tool_call_budget=ctx.tool_call_budget,
        mcp_dispatch=ctx.mcp_dispatch,
        activity_log=progress.activity_log,
        subagent_runs=progress.subagent_runs,
        update_activity=progress.update_activity,
        control=ctx.control,
        approval_policy=ctx.approval_policy,
        tracer=ctx.tracer,
    ):
        yield event
    observations = ctx.model.format_observation_messages(
        progress.model_message, batch.outputs, ctx.agent.get_template_vars()
    )
    ctx.session.add_messages(*observations)
    progress.tool_limit_reached = batch.tool_limit_reached


def _record_interrupted_reply(ctx: TurnContext, progress: TurnProgress) -> None:
    session, start_time = ctx.session, progress.start_time
    last_assistant = next(
        (
            message
            for message in reversed(session.messages)
            if message.get("role") == "assistant"
            and float((message.get("extra") or {}).get("timestamp") or 0) >= start_time
        ),
        None,
    )
    if last_assistant is not None and not ((last_assistant.get("extra") or {}).get("actions", [])):
        return
    partial = "".join(progress.streamed_response).strip()
    interrupted_content = (
        f"[本轮已中断，以下为已生成内容]\n{partial}" if partial else "（本轮已中断，尚未生成完整回答。）"
    )
    session.add_messages(
        {"role": "assistant", "content": interrupted_content, "extra": {"timestamp": start_time, "interrupted": True}}
    )


def _attach_activity(ctx: TurnContext, progress: TurnProgress, exit_status: str, duration: float) -> None:
    for event in progress.activity_log:
        if event["status"] == "working":
            event["status"] = "done" if event["kind"] == "status" else "error"
            event["detail"] = (
                "已中断" if exit_status == "interrupted" else ("" if event["kind"] == "status" else "未完成")
            )
    # Automatic compaction may replace the history list and move the original
    # turn index; timestamp matching keeps activity attached to this response.
    for message in reversed(ctx.session.messages):
        message_time = float((message.get("extra") or {}).get("timestamp") or 0)
        if message.get("role") == "assistant" and message_time >= progress.start_time:
            extra = dict(message.get("extra") or {})
            extra["activity"] = progress.activity_log
            if progress.subagent_runs:
                extra["subagents"] = progress.subagent_runs
            extra["duration"] = duration
            message["extra"] = extra
            break


def _final_reply(ctx: TurnContext, start_time: float) -> str:
    for message in reversed(ctx.session.messages):
        if (
            message.get("role") == "assistant"
            and float((message.get("extra") or {}).get("timestamp") or 0) >= start_time
        ):
            return str(message.get("content") or "")
    return ""


def _finish_turn(ctx: TurnContext, progress: TurnProgress) -> dict[str, Any]:
    """Record the outcome, persist the session, release turn state; returns the `finish` payload."""
    state, session, thread_id, request = ctx.state, ctx.session, ctx.thread_id, ctx.request
    duration = round(time.time() - progress.start_time, 2)
    exit_status = "error" if progress.model_failed else ("interrupted" if ctx.control.interrupted else "finish")
    if progress.model_failed:
        session.add_messages(
            {
                "role": "assistant",
                "content": progress.model_error_message,
                "extra": {"timestamp": progress.start_time, "error": True},
            }
        )
    if exit_status == "interrupted":
        _record_interrupted_reply(ctx, progress)
    _attach_activity(ctx, progress, exit_status, duration)

    # Persist normal sessions; ephemeral side conversations stay in memory only.
    if not request.ephemeral:
        session.save(state.get_session_file(session))
    if not request.ephemeral and session.group_id and ctx.group_registry:
        ctx.group_registry.update_agent_status(session.group_id, thread_id, "idle")

    finish_payload = {
        "duration": duration,
        "steps": progress.step_counter,
        "cost": round(ctx.agent.cost, 4),
        "total_cost": round(session.cost, 4),
        "exit_status": exit_status,
    }
    if ctx.tracer:
        finish_payload["trace_id"] = ctx.tracer.trace.trace_id
        ctx.tracer.turn_finished(
            exit_status=exit_status,
            steps=progress.step_counter,
            cost=float(ctx.agent.cost),
            output=_final_reply(ctx, progress.start_time),
        )
    state.active_chat_threads.discard(thread_id)
    if state.active_chat_message_ids.get(thread_id) == request.client_message_id:
        state.active_chat_message_ids.pop(thread_id, None)
        state.interruption_flags[thread_id] = False
    state.paused_chat_threads.discard(thread_id)
    state.chat_pause_events.pop(thread_id, None)
    return finish_payload


async def run_turn(ctx: TurnContext) -> AsyncIterator[str]:
    """Run one user turn described by ``ctx`` and yield its SSE event strings."""
    state, session, thread_id, control = ctx.state, ctx.session, ctx.thread_id, ctx.control
    progress = TurnProgress()
    state.active_chat_threads.add(thread_id)
    state.active_chat_message_ids[thread_id] = ctx.request.client_message_id
    if not ctx.request.ephemeral and session.group_id and ctx.group_registry:
        ctx.group_registry.update_agent_status(session.group_id, thread_id, "running")

    # This is a transport/model status, not a claim to expose hidden reasoning.
    progress.connection_status_id = f"status-{uuid.uuid4().hex[:8]}"
    progress.activity_log.append(
        {"id": progress.connection_status_id, "kind": "status", "label": "连接模型", "status": "working"}
    )
    yield sse("thinking", {"step": 0, "content": "正在连接模型…"})
    _append_user_message(ctx)

    # Explicit subagent requests are dispatched as actions immediately. The
    # model then receives the real result and writes the user-facing summary.
    if ctx.forced_delegate and ctx.request.content and not control.interrupted:
        async for event in _dispatch_forced_delegate(ctx, progress):
            yield event

    while not control.interrupted:
        progress.streamed_response = []
        await control.wait_if_paused()
        if control.interrupted:
            break
        progress.step_counter += 1
        async for event in model_step(ctx, progress):
            yield event
        if progress.model_message is None:
            break
        actions = progress.model_message.get("extra", {}).get("actions", [])
        if not actions:
            break
        async for event in _action_step(ctx, progress, actions):
            yield event
        if progress.tool_limit_reached or progress.step_counter >= ctx.tool_call_limit:
            break

    yield sse("finish", _finish_turn(ctx, progress))
    if ctx.request.ephemeral and session.metadata.get("closed"):
        state.sessions.pop(thread_id, None)
        state.interruption_flags.pop(thread_id, None)

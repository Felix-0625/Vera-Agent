"""The model half of a chat turn: compaction, request history, and one (streamed) model call.

`model_step` leaves the assistant message in ``progress.model_message`` and appends it to the
session; it is None when the turn was interrupted or the model failed (``progress.model_failed``).
Model spans are recorded on ``ctx.tracer`` when tracing is on.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from vera_agent.server.chat.progress import TurnProgress, sse
from vera_agent.server.chat.prompt import fill_context_placeholders
from vera_agent.server.chat.turn_setup import TurnContext
from vera_agent.tools.user_memory_tool import FORGET_USER_MEMORY_TOOL, REMEMBER_USER_TOOL

logger = logging.getLogger("vera_server.chat")


def repair_tool_call_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Close interrupted tool-call turns so providers accept the next request."""
    repaired: list[dict[str, Any]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        repaired.append(message)
        index += 1
        if message.get("role") != "assistant":
            continue
        expected = {
            str(call.get("id")): str((call.get("function") or {}).get("name") or "tool")
            for call in message.get("tool_calls") or []
            if call.get("id")
        }
        if not expected:
            continue
        while index < len(messages) and messages[index].get("role") == "tool":
            tool_message = messages[index]
            expected.pop(str(tool_message.get("tool_call_id") or ""), None)
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


async def _compact_if_needed(ctx: TurnContext, progress: TurnProgress) -> AsyncIterator[str]:
    # Main conversations are summarized automatically, but are never silently reborn; a rebirth
    # is reserved for subagents or an explicit grouped-workflow user action.
    from vera_agent.session.context_management import compact_session

    profile = ctx.model_profile
    try:
        compact_event = await asyncio.to_thread(
            compact_session, ctx.session, profile["name"], profile["model_kwargs"], profile["context_window"]
        )
    except Exception:
        logger.exception("Context compaction failed for %s; retaining original transcript", ctx.thread_id)
        compact_event = None
        progress.activity_log.append(
            {
                "id": f"compact-{uuid.uuid4().hex[:8]}",
                "kind": "status",
                "label": "上下文压缩失败",
                "detail": "保留原对话继续请求；若模型窗口不足，请切换模型或减少上下文。",
                "status": "error",
            }
        )
    if compact_event:
        progress.activity_log.append(
            {
                "id": f"compact-{uuid.uuid4().hex[:8]}",
                "kind": "status",
                "label": "压缩上下文",
                "detail": f"约 {compact_event['before_tokens']:,} → {compact_event['after_tokens']:,} Token（本地估算）",
                "status": "done",
            }
        )
        yield sse("context_management", compact_event)


def _build_chat_history(ctx: TurnContext) -> list[dict[str, Any]]:
    session, model = ctx.session, ctx.model
    if ctx.is_control_decision:
        # Repeated loop checks are independent evaluations; a prior verdict must not bias this check.
        current_user_turn = next(
            (message for message in reversed(session.messages) if message.get("role") == "user"), None
        )
        chat_history = [dict(current_user_turn)] if current_user_turn else []
    else:
        chat_history = [dict(message) for message in session.get_chat_history(prune_stale_observations=True)]
        chat_history = repair_tool_call_history(chat_history)
    rendered_system_prompt = fill_context_placeholders(ctx.system_prompt, ctx.context_prompt_vars)
    chat_history.insert(0, model.format_message(role="system", content=rendered_system_prompt))
    for history_message in chat_history:
        history_images = history_message.get("extra", {}).get("images", [])
        if history_message.get("role") != "user" or not history_images:
            continue
        multimodal_content = str(history_message.get("content", ""))
        for image in history_images:
            multimodal_content += (
                "\n<MSWEA_MULTIMODAL_CONTENT><CONTENT_TYPE>image_url</CONTENT_TYPE>"
                f"{image.get('data_url', '')}</MSWEA_MULTIMODAL_CONTENT>"
            )
        history_message["content"] = model.format_message(role="user", content=multimodal_content)["content"]
    return chat_history


def _model_query_kwargs(ctx: TurnContext) -> dict[str, Any]:
    if ctx.is_control_decision:
        return {"tools": [], "response_format": ctx.control_response_format}
    memory_tools = [REMEMBER_USER_TOOL, FORGET_USER_MEMORY_TOOL] if ctx.memory_tools_enabled else []
    return {"tools": ctx.agent.get_tools() + ctx.mcp_tools + memory_tools}


async def _stream_model(ctx: TurnContext, progress: TurnProgress, chat_history: list[dict]) -> AsyncIterator[str]:
    """Query a streaming model, forwarding text chunks; sets ``progress.model_message`` when done."""
    control, model = ctx.control, ctx.model
    stream_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    generation_status_id = ""
    query_kwargs = _model_query_kwargs(ctx)

    def forward_stream_text(text: str) -> None:
        control.pause_event.wait()
        if control.interrupted:
            raise InterruptedError("Chat response was interrupted.")
        loop.call_soon_threadsafe(stream_queue.put_nowait, ("text", text))

    def stream_worker() -> None:
        try:
            result = model.query_stream(chat_history, on_text=forward_stream_text, **query_kwargs)
            loop.call_soon_threadsafe(stream_queue.put_nowait, ("done", result))
        except Exception as error:
            loop.call_soon_threadsafe(stream_queue.put_nowait, ("error", error))

    worker_task = asyncio.create_task(asyncio.to_thread(stream_worker))
    while True:
        try:
            event_kind, event_value = await asyncio.wait_for(stream_queue.get(), timeout=2.5)
        except asyncio.TimeoutError:
            if control.interrupted:
                worker_task.cancel()
                return
            yield sse("thinking", {"step": 0, "content": "模型处理中，等待首个响应…"})
            continue
        await control.wait_if_paused()
        if control.interrupted:
            return
        if event_kind == "text":
            progress.streamed_response.append(str(event_value))
            if progress.connection_status_id:
                progress.update_activity(progress.connection_status_id, "done", "已连接")
                progress.connection_status_id = ""
            if not generation_status_id:
                generation_status_id = f"status-{uuid.uuid4().hex[:8]}"
                progress.activity_log.append(
                    {"id": generation_status_id, "kind": "status", "label": "生成回答", "status": "working"}
                )
                yield sse("thinking", {"step": 1, "content": "正在生成回答…"})
            yield sse("text_chunk", {"content": event_value})
        elif event_kind == "error":
            await worker_task
            raise event_value
        else:
            progress.model_message = event_value
            await worker_task
            if generation_status_id:
                progress.update_activity(generation_status_id, "done", "已接收模型输出")
            return


async def _query_model(ctx: TurnContext, progress: TurnProgress, chat_history: list[dict]) -> AsyncIterator[str]:
    progress.model_message = None
    if hasattr(ctx.model, "query_stream"):
        async for event in _stream_model(ctx, progress, chat_history):
            yield event
        return
    # Preserve compatibility with non-LiteLLM model adapters. These
    # adapters currently expose only a complete-response query API.
    progress.model_message = await asyncio.to_thread(ctx.model.query, chat_history, **_model_query_kwargs(ctx))
    response_content = progress.model_message.get("content", "")
    if response_content:
        yield sse("text_chunk", {"content": response_content})


async def model_step(ctx: TurnContext, progress: TurnProgress) -> AsyncIterator[str]:
    """One model call; leaves ``progress.model_message`` set on success, None when interrupted or failed."""
    tracer, step = ctx.tracer, progress.step_counter
    try:
        async for event in _compact_if_needed(ctx, progress):
            yield event
        chat_history = _build_chat_history(ctx)
        if tracer:
            tracer.model_started(step, ctx.model_profile["name"], len(chat_history))
        async for event in _query_model(ctx, progress, chat_history):
            yield event
        if ctx.control.interrupted:
            progress.model_message = None
            if tracer:
                tracer.model_finished(step, None, "interrupted")
            return
        ctx.session.add_messages(progress.model_message)
        if tracer:
            tracer.model_finished(step, progress.model_message)
    except Exception as error:
        progress.model_message = None
        if ctx.control.interrupted:
            return
        progress.model_error_message = f"Model inference error: {error}"
        progress.model_failed = True
        if tracer:
            tracer.model_finished(step, None, progress.model_error_message)
        yield sse("text_chunk", {"content": progress.model_error_message})

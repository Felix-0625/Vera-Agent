"""Agent chat execution routes.

Routes:
- POST /api/chat/stream: run one user turn and stream Server-Sent Events
- POST /api/chat/confirm: answer a pending tool-approval request
- POST /api/chat/interrupt, /api/chat/pause, /api/chat/resume: control a running turn
- POST /api/chat/ephemeral/close: discard an ephemeral (side chat) session

The stream route only builds the turn context (`server/chat/turn_setup.py`), connects attached
MCP servers, and forwards the events of `server/chat/turn.py:run_turn`. Every turn is traced into
the local trace store and scored once it finishes (`vera_agent/telemetry`).
"""

from __future__ import annotations

import logging
import time
from contextlib import AsyncExitStack

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.evolution.active_profile import extend_with_active_profile
from vera_agent.memory.consolidate import schedule_after_turn
from vera_agent.server.chat.mcp_session import connect_attached_mcps
from vera_agent.server.chat.model_step import repair_tool_call_history
from vera_agent.server.chat.prompt import enabled_attached_skills, fill_context_placeholders
from vera_agent.server.chat.request import ChatRequestError
from vera_agent.server.chat.turn import run_turn
from vera_agent.server.chat.turn_setup import explicit_subagent_request, prepare_turn
from vera_agent.server.state import ServerState
from vera_agent.telemetry.recorder import attach_turn_tracer

# Kept for callers and tests that import these helpers from the route module.
_enabled_attached_skills = enabled_attached_skills
_explicit_subagent_request = explicit_subagent_request
_fill_context_placeholders = fill_context_placeholders
_repair_tool_call_history = repair_tool_call_history

logger = logging.getLogger("vera_server.chat")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def chat_stream(request: Request) -> StreamingResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        ctx = prepare_turn(state, body, prompt_extender=extend_with_active_profile(state))
    except ChatRequestError as error:
        return error.response()
    memory_enabled = ctx.context_settings["memory_enabled"]
    # Runs after the trace is persisted and scored, so episodes carry the outcome score.
    attach_turn_tracer(ctx, on_finish=[lambda trace: schedule_after_turn(state, trace, memory_enabled=memory_enabled)])

    async def sse_event_generator():
        async with AsyncExitStack() as stack:
            async for notice in connect_attached_mcps(
                stack, state, ctx.request.attached_mcps, ctx.target_cwd, ctx.mcp_tools, ctx.mcp_dispatch
            ):
                yield notice
            ctx.model.config.dynamic_tool_names = list(ctx.mcp_dispatch)
            if ctx.memory_tools_enabled:
                ctx.model.config.dynamic_tool_names.extend(["remember_user", "forget_user_memory"])
            async for event in run_turn(ctx):
                yield event

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
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

"""Sessions lifecycle, attachment, health check, and direct message bus dispatch."""

from __future__ import annotations

import logging
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.sessions")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def health(request: Request) -> JSONResponse:
    state = _get_state(request)
    return JSONResponse({"status": "ok", "repo_root": str(state.root_path)})


async def attach_session(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    thread_id = body.get("thread_id")
    group_id = body.get("group_id")
    if not thread_id or not group_id:
        return JSONResponse({"error": "thread_id and group_id required"}, status_code=400)

    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    success = state.graph.attach_session_to_group(thread_id, group_id)
    return JSONResponse({"success": success})


async def detach_session(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    thread_id = body.get("thread_id")
    if not thread_id:
        return JSONResponse({"error": "thread_id required"}, status_code=400)

    if not state.graph:
        return JSONResponse({"error": "Graph not initialized"}, status_code=500)

    success = state.graph.detach_session(thread_id)
    return JSONResponse({"success": success})


async def send_message(request: Request) -> JSONResponse:
    """Dispatches message into session bus."""
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    thread_id = body.get("thread_id")
    content = body.get("content", "").strip()
    sender_id = body.get("sender_id", "user")

    if not thread_id or not content:
        return JSONResponse({"error": "thread_id and content required"}, status_code=400)

    session = state.get_or_create_session(thread_id)
    session.add_messages({
        "role": "user" if sender_id == "user" else "system",
        "content": content,
        "extra": {"sender_id": sender_id},
    })
    session.save(state.get_sessions_dir() / f"{thread_id}.json")

    return JSONResponse({"status": "delivered", "thread_id": thread_id, "messages_count": len(session.messages)})


session_routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/sessions/attach", attach_session, methods=["POST"]),
    Route("/api/sessions/detach", detach_session, methods=["POST"]),
    Route("/api/messages/send", send_message, methods=["POST"]),
]

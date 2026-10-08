"""Global threads management, search, messages replay, and SideChat context probe."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.threads")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_all_threads(request: Request) -> JSONResponse:
    state = _get_state(request)
    params = request.query_params
    search_q = params.get("search", "").strip().lower()
    group_id_filter = params.get("group_id")
    is_archived_param = params.get("is_archived")

    # Ensure disk sessions are indexed
    sessions_dir = state.get_sessions_dir()
    for f in sessions_dir.glob("*.json"):
        tid = f.stem
        if tid not in state.sessions:
            try:
                state.sessions[tid] = ThreadSession.load(f)
            except Exception:
                pass

    results = []
    for s in state.sessions.values():
        if group_id_filter and s.group_id != group_id_filter:
            continue
        if is_archived_param is not None:
            wanted_archived = is_archived_param.lower() in ("true", "1")
            if s.is_archived != wanted_archived:
                continue

        if search_q:
            match_title = search_q in (s.title or "").lower()
            match_tid = search_q in s.thread_id.lower()
            match_msgs = any(
                search_q in str(m.get("content", "")).lower()
                for m in s.messages
            )
            if not (match_title or match_tid or match_msgs):
                continue

        results.append(s.to_dict())

    # Sort pinned first, then newest
    results.sort(key=lambda t: (not t.get("is_pinned", False), -t.get("created_at", 0)))
    return JSONResponse({"threads": results})


async def create_thread(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    title = body.get("title", "New Conversation")
    role = body.get("role", "main")
    group_id = body.get("group_id")
    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"

    session = ThreadSession(
        thread_id=thread_id,
        group_id=group_id,
        role=role,
        title=title,
    )
    state.sessions[thread_id] = session
    if group_id and state.graph:
        group = state.graph.get_group(group_id)
        if group:
            group.add_thread(thread_id)
        state.graph.register_session(thread_id, role=role, group_id=group_id, title=title)
        if state.registry_mgr:
            state.registry_mgr.register_agent(
                group_id=group_id,
                thread_id=thread_id,
                title=title,
                role=role,
                log_uri=f".agents/sessions/{thread_id}.json",
                status="idle",
            )

    session.save(state.get_sessions_dir() / f"{thread_id}.json")
    return JSONResponse(session.to_dict())


async def get_thread_messages(request: Request) -> JSONResponse:
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.get_or_create_session(thread_id)
    return JSONResponse({
        "thread_id": session.thread_id,
        "title": session.title,
        "role": session.role,
        "is_pinned": session.is_pinned,
        "is_archived": session.is_archived,
        "cost": round(session.cost, 4),
        "n_calls": session.n_calls,
        "messages": session.messages,
    })


async def update_thread(request: Request) -> JSONResponse:
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.get_or_create_session(thread_id)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if "title" in body:
        session.title = str(body["title"])
        if session.group_id and state.registry_mgr:
            state.registry_mgr.register_agent(
                group_id=session.group_id,
                thread_id=thread_id,
                title=session.title,
                role=session.role,
            )
    if "is_pinned" in body:
        session.is_pinned = bool(body["is_pinned"])
    if "is_archived" in body:
        session.is_archived = bool(body["is_archived"])
    if "role" in body:
        session.role = str(body["role"])

    session.save(state.get_sessions_dir() / f"{thread_id}.json")
    return JSONResponse(session.to_dict())


async def delete_thread(request: Request) -> JSONResponse:
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.sessions.get(thread_id)
    if session and session.group_id and state.registry_mgr:
        state.registry_mgr.remove_agent(session.group_id, thread_id)
    state.sessions.pop(thread_id, None)
    if state.graph:
        state.graph.remove_session(thread_id)

    s_file = state.get_sessions_dir() / f"{thread_id}.json"
    if s_file.exists():
        s_file.unlink()

    return JSONResponse({"status": "ok", "deleted_thread_id": thread_id})


async def probe_thread_context(request: Request) -> JSONResponse:
    """Lightweight context probe for SideChatTab ('探查主对话上下文并挂载')."""
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.get_or_create_session(thread_id)

    last_user_msg = ""
    last_assistant_msg = ""
    for m in reversed(session.messages):
        if m.get("role") == "user" and not last_user_msg:
            last_user_msg = str(m.get("content", ""))
        elif m.get("role") == "assistant" and not last_assistant_msg:
            last_assistant_msg = str(m.get("content", ""))
        if last_user_msg and last_assistant_msg:
            break

    summary = last_user_msg[:300] if last_user_msg else (session.title or "")
    return JSONResponse({
        "thread_id": session.thread_id,
        "title": session.title,
        "role": session.role,
        "message_count": len(session.messages),
        "last_user_message": last_user_msg,
        "last_assistant_message": last_assistant_msg,
        "summary": summary,
    })


thread_routes = [
    Route("/api/threads", get_all_threads, methods=["GET"]),
    Route("/api/threads", create_thread, methods=["POST"]),
    Route("/api/threads/{thread_id}/messages", get_thread_messages, methods=["GET"]),
    Route("/api/threads/{thread_id}", update_thread, methods=["PATCH"]),
    Route("/api/threads/{thread_id}", delete_thread, methods=["DELETE"]),
    Route("/api/threads/{thread_id}/context-probe", probe_thread_context, methods=["GET"]),
]

"""Conversation (thread) routes.

Routes: GET/POST /api/threads, PATCH/DELETE /api/threads/{id},
GET /api/threads/{id}/messages, POST /api/threads/{id}/messages/deliver
(deliver a workflow result to the originating chat), POST /api/threads/{id}/messages/truncate,
GET /api/threads/{id}/context-status, GET /api/context-status,
POST /api/threads/{id}/context-rebirth.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.model_profile import resolve_model_profile
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

    # Index sessions from every bound project so the sidebar and history modal
    # keep working after the user switches the active project.
    history = state.load_json_config("projects_history.json", {"projects": []})
    session_roots = {
        str(Path(project["path"]).resolve()): (Path(project["path"]).resolve(), project.get("id"))
        for project in history.get("projects", [])
        if project.get("path") and Path(project["path"]).is_dir()
    }
    session_roots.setdefault(str(state.root_path.resolve()), (state.root_path.resolve(), None))
    for project_root, project_id in session_roots.values():
        for session_file in (project_root / ".agents" / "sessions").glob("*.json"):
            tid = session_file.stem
            if tid in state.sessions:
                continue
            try:
                session = ThreadSession.load(session_file)
                session.project_id = state.infer_legacy_session_project_id(session_file, session, project_id)
                session.metadata.setdefault("project_root", str(project_root))
                state.sessions[tid] = session
            except Exception:
                logger.exception("Unable to load conversation %s", tid)

    results = []
    for s in state.sessions.values():
        if s.metadata.get("ephemeral"):
            continue
        if group_id_filter and s.group_id != group_id_filter:
            continue
        if is_archived_param is not None:
            wanted_archived = is_archived_param.lower() in ("true", "1")
            if s.is_archived != wanted_archived:
                continue

        if search_q:
            match_title = search_q in (s.title or "").lower()
            match_tid = search_q in s.thread_id.lower()
            match_msgs = any(search_q in str(m.get("content", "")).lower() for m in s.messages)
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
    project_id = body.get("project_id")
    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"

    session = ThreadSession(
        thread_id=thread_id,
        group_id=group_id,
        project_id=project_id,
        role=role,
        title=title,
    )
    if project_id:
        try:
            session.metadata["project_root"] = str(state.get_project_root(project_id))
        except ValueError as error:
            return JSONResponse({"error": str(error)}, status_code=404)
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

    session.save(state.get_session_file(session))
    return JSONResponse(session.to_dict())


async def get_thread_messages(request: Request) -> JSONResponse:
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.get_or_create_session(thread_id)
    return JSONResponse(
        {
            "thread_id": session.thread_id,
            "title": session.title,
            "role": session.role,
            "is_pinned": session.is_pinned,
            "is_archived": session.is_archived,
            "cost": round(session.cost, 4),
            "n_calls": session.n_calls,
            "messages": session.messages,
        }
    )


async def deliver_orchestration_result(request: Request) -> JSONResponse:
    """Persist a completed orchestration as an assistant reply in its caller thread."""
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    content = str(body.get("content", "")).strip()
    task_input = str(body.get("input", "")).strip()
    run_id = str(body.get("run_id", "")).strip()
    group_id = str(body.get("group_id", "")).strip()
    if not content or not run_id or not group_id:
        return JSONResponse({"error": "content, run_id, and group_id are required"}, status_code=400)
    session = state.sessions.get(thread_id)
    if session is None:
        session_file = state.get_session_file(session)
        if session_file.exists():
            session = ThreadSession.load(session_file)
            state.sessions[thread_id] = session
    if session is None:
        return JSONResponse({"error": "Caller conversation not found"}, status_code=404)
    if body.get("project_id") and session.project_id and session.project_id != str(body["project_id"]):
        return JSONResponse({"error": "Caller conversation belongs to a different project"}, status_code=409)
    existing = next(
        (
            message
            for message in session.messages
            if message.get("role") == "assistant" and (message.get("extra") or {}).get("orchestration_run_id") == run_id
        ),
        None,
    )
    if existing:
        return JSONResponse({"status": "already_delivered", "messages": [existing]})
    delivered = []
    if task_input and not any(
        message.get("role") == "user" and (message.get("extra") or {}).get("orchestration_run_id") == run_id
        for message in session.messages
    ):
        delivered.extend(
            session.add_messages(
                {
                    "role": "user",
                    "content": task_input,
                    "extra": {"orchestration_run_id": run_id, "orchestration_group_id": group_id, "sender_id": "user"},
                    "timestamp": time.time(),
                }
            )
        )
    delivered.extend(
        session.add_messages(
            {
                "role": "assistant",
                "content": content,
                "extra": {
                    "orchestration_run_id": run_id,
                    "orchestration_group_id": group_id,
                    "sender_id": "supervisor",
                },
                "timestamp": time.time(),
            }
        )
    )
    session.save(state.get_session_file(session))
    return JSONResponse({"status": "delivered", "messages": delivered})


async def truncate_from_user_message(request: Request) -> JSONResponse:
    """Remove a user message and all later turns before edited text is resent."""
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.get_or_create_session(thread_id)
    if thread_id in state.active_chat_threads:
        return JSONResponse({"error": "Cannot edit a message while its response is running."}, status_code=409)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    message_id = str(body.get("message_id") or "")
    index = next(
        (
            i
            for i, message in enumerate(session.messages)
            if message.get("id") == message_id and message.get("role") == "user"
        ),
        None,
    )
    if index is None:
        return JSONResponse(
            {"error": "Editable user message not found. New messages support edit and resend."}, status_code=404
        )
    session.messages = session.messages[:index]
    # A checkpoint may summarize the message being edited, so rebuild model
    # context from the surviving raw transcript after an edit-and-resend.
    session.metadata.pop("context_checkpoints", None)
    session.updated_at = __import__("time").time()
    session.save(state.get_session_file(session))
    return JSONResponse({"status": "ok", "removed_from": index})


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

    session.save(state.get_session_file(session))
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

    session = session or state.get_or_create_session(thread_id)
    s_file = state.get_session_file(session)
    if s_file.exists():
        s_file.unlink()

    return JSONResponse({"status": "ok", "deleted_thread_id": thread_id})


async def get_thread_context_status(request: Request) -> JSONResponse:
    """Return context data for a thread, or model capacity for a new draft."""
    state = _get_state(request)
    thread_id = request.path_params.get("thread_id", "")
    session = state.sessions.get(thread_id) if thread_id else None
    if thread_id and session is None:
        session_file = state.get_sessions_dir() / f"{thread_id}.json"
        if not session_file.is_file():
            return JSONResponse({"error": "Thread not found"}, status_code=404)
        try:
            session = ThreadSession.load(session_file)
        except Exception:
            return JSONResponse({"error": "Thread could not be loaded"}, status_code=500)

    try:
        profile = resolve_model_profile(state, request.query_params.get("model_id"))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    samples = []
    rebirth_logs = []
    for message in session.messages if session else []:
        extra = message.get("extra") or {}
        response = extra.get("response") or {}
        usage = response.get("usage") or {}
        if message.get("role") == "assistant" and usage:
            tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            if tokens is not None:
                timestamp = float(extra.get("timestamp") or response.get("created") or message.get("created") or 0)
                samples.append(
                    {
                        "timestamp": timestamp,
                        "tokens": int(tokens),
                        "model": str(response.get("model") or profile["name"]),
                    }
                )
        if extra.get("compaction") or extra.get("context_rebirth"):
            if extra.get("compaction"):
                folded = extra.get("folded_message_count")
                kept = extra.get("kept_message_count")
                detail = (
                    f"折叠 {folded} 条早期消息，保留最近 {kept} 条"
                    if folded is not None and kept is not None
                    else "早期对话已整理为上下文锚点"
                )
            else:
                detail = str(extra.get("reason") or "创建衔接会话并注入交接摘要")
            rebirth_logs.append(
                {
                    "timestamp": float(extra.get("timestamp") or 0),
                    "kind": "压缩" if extra.get("compaction") else "换血",
                    "detail": detail,
                }
            )

    related_sessions: list[ThreadSession] = list(state.sessions.values())
    for file in state.get_sessions_dir().glob("*.json"):
        if file.stem not in state.sessions:
            try:
                related_sessions.append(ThreadSession.load(file))
            except Exception:
                continue
    for related in related_sessions:
        if related.thread_id == thread_id and related.parent_thread_id and related.metadata.get("rebirth_timestamp"):
            rebirth_logs.append(
                {
                    "timestamp": related.metadata["rebirth_timestamp"],
                    "kind": "换血",
                    "detail": f"由会话 {related.parent_thread_id} 衔接",
                }
            )
        elif related.parent_thread_id == thread_id and related.metadata.get("rebirth_timestamp"):
            rebirth_logs.append(
                {
                    "timestamp": related.metadata["rebirth_timestamp"],
                    "kind": "换血",
                    "detail": f"衔接到会话 {related.thread_id}",
                }
            )

    samples.sort(key=lambda item: item["timestamp"])
    recorded_timestamps = {(item["kind"], round(item["timestamp"], 3)) for item in rebirth_logs}
    for event in session.metadata.get("context_events", []) if session else []:
        timestamp = float(event.get("timestamp") or 0)
        kind = str(event.get("kind") or "压缩")
        if timestamp and (kind, round(timestamp, 3)) not in recorded_timestamps:
            rebirth_logs.append(
                {
                    "timestamp": timestamp,
                    "kind": kind,
                    "detail": str(
                        event.get("detail")
                        or f"{event.get('before_tokens', '?')} → {event.get('after_tokens', '?')} Token"
                    ),
                }
            )
            recorded_timestamps.add((kind, round(timestamp, 3)))
    rebirth_logs.sort(key=lambda item: item["timestamp"])
    latest = samples[-1] if samples else None
    max_tokens = profile["context_window"]
    return JSONResponse(
        {
            "thread_id": thread_id or None,
            "model": profile["name"],
            "context_limit": max_tokens,
            "context_limit_source": profile["context_source"],
            "used_tokens": latest["tokens"] if latest else (0 if not thread_id else None),
            "used_percent": round(latest["tokens"] / max_tokens * 100, 2)
            if latest and max_tokens
            else (0 if not thread_id and max_tokens else None),
            "rebirth_logs": rebirth_logs,
            "can_manual_rebirth": bool(session and session.group_id),
        }
    )


async def rebirth_group_thread_context(request: Request) -> JSONResponse:
    """User-triggered context epoch rotation for one idle group thread."""
    state = _get_state(request)
    thread_id = request.path_params["thread_id"]
    session = state.sessions.get(thread_id)
    if session is None:
        session_file = state.get_sessions_dir() / f"{thread_id}.json"
        if session_file.is_file():
            try:
                session = ThreadSession.load(session_file)
                state.sessions[thread_id] = session
            except Exception:
                session = None
    if session is None:
        return JSONResponse({"error": "Thread not found"}, status_code=404)
    if not session.group_id:
        return JSONResponse(
            {"error": "Manual context rebirth is only available for group workflow threads."}, status_code=403
        )
    if thread_id in state.active_chat_threads:
        return JSONResponse(
            {"error": "Pause or finish this thread before starting a new context epoch."}, status_code=409
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        profile = resolve_model_profile(state, body.get("model_id"))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    from vera_agent.session.context_management import compact_session

    archive = state.get_sessions_dir() / f"{thread_id}.epoch-{int(time.time())}.json"
    session.save(archive)
    event = compact_session(
        session,
        profile["name"],
        profile["model_kwargs"],
        profile["context_window"],
        force=True,
        keep_recent_tokens=0,
        reason="manual_rebirth",
    )
    if not event:
        archive.unlink(missing_ok=True)
        return JSONResponse(
            {
                "error": "The current history is too short or the model context limit is unavailable; no rebirth was performed."
            },
            status_code=409,
        )

    rebirth_event = {
        "kind": "换血",
        "timestamp": time.time(),
        "detail": "用户手动开始新上下文阶段；完整轨迹归档，工作流节点与分组关系保持不变",
        "archive": archive.name,
        "before_tokens": event["before_tokens"],
        "after_tokens": event["after_tokens"],
    }
    session.metadata.setdefault("context_events", []).append(rebirth_event)
    session.save(state.get_session_file(session))
    return JSONResponse({"status": "reborn", "event": rebirth_event})


thread_routes = [
    Route("/api/threads", get_all_threads, methods=["GET"]),
    Route("/api/threads", create_thread, methods=["POST"]),
    Route("/api/threads/{thread_id}/messages", get_thread_messages, methods=["GET"]),
    Route("/api/threads/{thread_id}/messages/deliver", deliver_orchestration_result, methods=["POST"]),
    Route("/api/threads/{thread_id}/messages/truncate", truncate_from_user_message, methods=["POST"]),
    Route("/api/threads/{thread_id}", update_thread, methods=["PATCH"]),
    Route("/api/threads/{thread_id}", delete_thread, methods=["DELETE"]),
    Route("/api/threads/{thread_id}/context-status", get_thread_context_status, methods=["GET"]),
    Route("/api/context-status", get_thread_context_status, methods=["GET"]),
    Route("/api/threads/{thread_id}/context-rebirth", rebirth_group_thread_context, methods=["POST"]),
]

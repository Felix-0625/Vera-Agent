"""Scoped memory routes for the memory panel.

Routes:
- GET /api/memories: active memories (query: scope, scope_id, kind, status=active|deleted|any)
- POST /api/memories: create a memory as the user (body: scope, scope_id, kind, content)
- PATCH /api/memories/{memory_id}: revise content or kind as the user
- DELETE /api/memories/{memory_id}: soft delete
- GET /api/memories/{memory_id}/history: every version with reason, actor and trace id
- POST /api/memories/{memory_id}/restore: make an earlier version current again (body: version)
- GET /api/memories/pending: changes proposed by consolidation that wait for confirmation
- POST /api/memories/pending/{change_id}: accept or reject a pending change (body: accept)
- GET /api/settings/memory, PUT /api/settings/memory: backend, consolidation and recall budget

The older `/api/settings/user-memories` routes (settings.py) keep working on the user scope.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.memory.records import KINDS, SCOPES
from vera_agent.memory.service import (
    MemoryWriteError,
    load_memory_config,
    memory_service_for_state,
    save_memory_config,
)
from vera_agent.server.state import ServerState


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _service(request: Request):
    return memory_service_for_state(_get_state(request))


async def _json_body(request: Request) -> dict | None:
    try:
        body = await request.json()
    except Exception:
        return None
    return body if isinstance(body, dict) else None


async def list_memories(request: Request) -> JSONResponse:
    params = request.query_params
    service = _service(request)
    status = params.get("status", "active")
    if status not in {"active", "deleted", "superseded", "any"}:
        return JSONResponse({"error": "Unsupported status filter."}, status_code=400)
    scope = params.get("scope")
    if scope and scope not in SCOPES:
        return JSONResponse({"error": "Unsupported scope."}, status_code=400)
    scopes = service.backend.scopes()
    if scope:
        scopes = [
            pair
            for pair in scopes
            if pair[0] == scope and (not params.get("scope_id") or pair[1] == params["scope_id"])
        ]
    kinds = [params["kind"]] if params.get("kind") in KINDS else None
    records = service.backend.list(scopes, kinds=kinds, status=status)
    return JSONResponse({"memories": [record.to_dict() for record in records]})


async def create_memory(request: Request) -> JSONResponse:
    body = await _json_body(request)
    if body is None:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    try:
        record = _service(request).add(
            scope=str(body.get("scope") or "user"),
            scope_id=str(body.get("scope_id") or ""),
            kind=str(body.get("kind") or ""),
            content=str(body.get("content") or ""),
            source="user",
        )
    except MemoryWriteError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"memory": record.to_dict()}, status_code=201)


async def update_memory(request: Request) -> JSONResponse:
    body = await _json_body(request)
    if body is None or not isinstance(body.get("content"), str):
        return JSONResponse({"error": "content is required."}, status_code=400)
    try:
        record = _service(request).revise(
            request.path_params["memory_id"], body["content"], actor="user", kind=body.get("kind") or None
        )
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except MemoryWriteError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"memory": record.to_dict()})


async def delete_memory(request: Request) -> JSONResponse:
    if not _service(request).delete(request.path_params["memory_id"], actor="user"):
        return JSONResponse({"error": "Memory not found."}, status_code=404)
    return JSONResponse({"status": "deleted"})


async def memory_history(request: Request) -> JSONResponse:
    history = _service(request).backend.history(request.path_params["memory_id"])
    if not history:
        return JSONResponse({"error": "Memory not found."}, status_code=404)
    return JSONResponse({"history": history})


async def restore_memory(request: Request) -> JSONResponse:
    body = await _json_body(request)
    try:
        version = int((body or {}).get("version"))
        record = _service(request).restore_version(request.path_params["memory_id"], version)
    except (TypeError, ValueError):
        return JSONResponse({"error": "version must be an integer."}, status_code=400)
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    return JSONResponse({"memory": record.to_dict()})


async def list_pending(request: Request) -> JSONResponse:
    return JSONResponse({"changes": _service(request).pending_changes()})


async def resolve_pending(request: Request) -> JSONResponse:
    body = await _json_body(request)
    if body is None or not isinstance(body.get("accept"), bool):
        return JSONResponse({"error": "accept (boolean) is required."}, status_code=400)
    try:
        change = _service(request).resolve_change(request.path_params["change_id"], body["accept"])
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except MemoryWriteError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"change": change})


async def get_memory_settings(request: Request) -> JSONResponse:
    return JSONResponse(load_memory_config(_get_state(request)))


async def update_memory_settings(request: Request) -> JSONResponse:
    body = await _json_body(request)
    if body is None:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    return JSONResponse(save_memory_config(_get_state(request), body))


memory_routes = [
    Route("/api/memories", list_memories, methods=["GET"]),
    Route("/api/memories", create_memory, methods=["POST"]),
    Route("/api/memories/pending", list_pending, methods=["GET"]),
    Route("/api/memories/pending/{change_id}", resolve_pending, methods=["POST"]),
    Route("/api/memories/{memory_id}", update_memory, methods=["PATCH"]),
    Route("/api/memories/{memory_id}", delete_memory, methods=["DELETE"]),
    Route("/api/memories/{memory_id}/history", memory_history, methods=["GET"]),
    Route("/api/memories/{memory_id}/restore", restore_memory, methods=["POST"]),
    Route("/api/settings/memory", get_memory_settings, methods=["GET"]),
    Route("/api/settings/memory", update_memory_settings, methods=["PUT"]),
]

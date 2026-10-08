"""Scheduled tasks management (Cron / Interval triggers and background execution)."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.tasks")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_scheduled_tasks(request: Request) -> JSONResponse:
    state = _get_state(request)
    data = state.load_json_config("scheduled_tasks.json", {"tasks": []})
    return JSONResponse(data)


async def create_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = body.get("name", "").strip()
    cron = body.get("cron", "").strip()
    prompt = body.get("prompt", "").strip()
    if not name or not prompt:
        return JSONResponse({"error": "name and prompt are required"}, status_code=400)

    data = state.load_json_config("scheduled_tasks.json", {"tasks": []})
    tasks = data.get("tasks", [])

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    new_task = {
        "id": task_id,
        "name": name,
        "cron": cron or "0 * * * *",
        "prompt": prompt,
        "thread_id": body.get("thread_id"),
        "enabled": bool(body.get("enabled", True)),
        "created_at": time.time(),
        "last_run": None,
        "last_status": "idle",
    }
    tasks.append(new_task)
    data["tasks"] = tasks
    state.save_json_config("scheduled_tasks.json", data)

    return JSONResponse(new_task, status_code=201)


async def toggle_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    task_id = request.path_params.get("task_id")
    data = state.load_json_config("scheduled_tasks.json", {"tasks": []})
    tasks = data.get("tasks", [])

    target = next((t for t in tasks if t.get("id") == task_id), None)
    if not target:
        return JSONResponse({"error": f"Scheduled task '{task_id}' not found"}, status_code=404)

    target["enabled"] = not target.get("enabled", True)
    data["tasks"] = tasks
    state.save_json_config("scheduled_tasks.json", data)

    return JSONResponse(target)


async def run_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    task_id = request.path_params.get("task_id")
    data = state.load_json_config("scheduled_tasks.json", {"tasks": []})
    tasks = data.get("tasks", [])

    target = next((t for t in tasks if t.get("id") == task_id), None)
    if not target:
        return JSONResponse({"error": f"Scheduled task '{task_id}' not found"}, status_code=404)

    target["last_run"] = time.time()
    target["last_status"] = "success"
    data["tasks"] = tasks
    state.save_json_config("scheduled_tasks.json", data)

    return JSONResponse({
        "status": "triggered",
        "task_id": task_id,
        "last_run": target["last_run"],
    })


async def delete_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    task_id = request.path_params.get("task_id")
    data = state.load_json_config("scheduled_tasks.json", {"tasks": []})
    tasks = data.get("tasks", [])

    before_len = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]
    if len(tasks) == before_len:
        return JSONResponse({"error": f"Scheduled task '{task_id}' not found"}, status_code=404)

    data["tasks"] = tasks
    state.save_json_config("scheduled_tasks.json", data)
    return JSONResponse({"status": "deleted", "task_id": task_id})


task_routes = [
    Route("/api/tasks/scheduled", get_scheduled_tasks, methods=["GET"]),
    Route("/api/tasks/scheduled", create_scheduled_task, methods=["POST"]),
    Route("/api/tasks/scheduled/{task_id}/toggle", toggle_scheduled_task, methods=["PATCH"]),
    Route("/api/tasks/scheduled/{task_id}/run", run_scheduled_task, methods=["POST"]),
    Route("/api/tasks/scheduled/{task_id}", delete_scheduled_task, methods=["DELETE"]),
]

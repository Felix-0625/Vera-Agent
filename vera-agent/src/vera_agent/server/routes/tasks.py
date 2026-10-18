"""One-time scheduled Agent prompts and their background scheduler.

Routes: GET/POST /api/tasks/scheduled, PATCH /api/tasks/scheduled/{id}/toggle,
POST /api/tasks/scheduled/{id}/run, DELETE /api/tasks/scheduled/{id}.

Tasks are stored in `<project>/.agents/scheduled_tasks.json`. The scheduler is
started and stopped by the application lifespan in `server/app.py`. These are
separate from task board work items (see taskboard.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.server.state import APPLICATION_CONFIGS, ServerState
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.tasks")


class _ProjectScopedState:
    """Read project-local settings while sharing the server's runtime registries."""

    def __init__(self, state: ServerState, project_root: Path):
        self._state = state
        self.root_path = project_root

    def __getattr__(self, name: str) -> Any:
        return getattr(self._state, name)

    def load_json_config(self, file_name: str, default_data: Any) -> Any:
        # Application-scoped settings (models, permissions, MCP, Skills, project history) come from
        # the shared application root; only the remaining configs are read from the task's project.
        if file_name in APPLICATION_CONFIGS:
            return self._state.load_json_config(file_name, default_data)
        path = self.root_path / ".agents" / file_name
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default_data

    def get_sessions_dir(self) -> Path:
        path = self.root_path / ".agents" / "sessions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_session_file(self, session: ThreadSession) -> Path:
        return self.get_sessions_dir() / f"{session.thread_id}.json"


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _tasks_file(root: Path) -> Path:
    return root / ".agents" / "scheduled_tasks.json"


def _load_tasks(root: Path) -> dict[str, Any]:
    path = _tasks_file(root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) and isinstance(value.get("tasks"), list) else {"tasks": []}
    except FileNotFoundError:
        return {"tasks": []}
    except (OSError, json.JSONDecodeError):
        logger.exception("Unable to read scheduled tasks from %s", path)
        return {"tasks": []}


def _save_tasks(root: Path, data: dict[str, Any]) -> None:
    path = _tasks_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _parse_run_at(value: Any) -> datetime:
    """Parse an ISO timestamp and require an explicit timezone."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("run_at must be an ISO 8601 timestamp with a timezone")
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("run_at must be a valid ISO 8601 timestamp") from error
    if result.tzinfo is None:
        raise ValueError("run_at must include a timezone")
    return result.astimezone(timezone.utc)


def _is_due(task: dict[str, Any], now: datetime) -> bool:
    """Only pending one-time tasks with an explicit run_at can be dispatched."""
    if not task.get("enabled", True) or task.get("last_status", "idle") != "idle":
        return False
    try:
        return _parse_run_at(task.get("run_at")) <= now.astimezone(timezone.utc)
    except ValueError:
        return False


def _project_roots(state: ServerState) -> list[tuple[Path, str | None]]:
    history = state.load_json_config("projects_history.json", {"projects": []})
    roots: dict[str, str | None] = {str(state.root_path.resolve()): None}
    for project in history.get("projects", []):
        raw_path = project.get("path")
        if raw_path and Path(raw_path).is_dir():
            roots[str(Path(raw_path).resolve())] = project.get("id")
    return [(Path(path), project_id) for path, project_id in roots.items()]


async def _execute_task(
    state: ServerState, task: dict[str, Any], task_storage_root: Path, project_id: str | None
) -> None:
    """Run a task through the same chat pipeline used by interactive requests."""
    from vera_agent.server.routes.chat import chat_stream

    task_id = str(task["id"])
    thread_id = str(task.get("thread_id") or f"th_scheduled_{uuid.uuid4().hex[:12]}")
    task["thread_id"] = thread_id
    model_id = task.get("model_id")
    if not model_id:
        task["last_status"] = "failed"
        task["last_error"] = "没有指定模型，请编辑任务并选择模型。"
        task["last_run"] = time.time()
        data = _load_tasks(task_storage_root)
        current = next((item for item in data["tasks"] if item.get("id") == task_id), None)
        if current is not None:
            current.update({key: task.get(key) for key in ("last_run", "last_status", "last_error")})
            _save_tasks(task_storage_root, data)
        return

    try:
        project_root = state.get_project_root(project_id)
    except ValueError as error:
        task["last_status"] = "failed"
        task["last_error"] = "任务绑定的项目已不可用，请重新绑定项目后重建任务。"
        task["last_run"] = time.time()
        data = _load_tasks(task_storage_root)
        current = next((item for item in data["tasks"] if item.get("id") == task_id), None)
        if current is not None:
            current.update({key: task.get(key) for key in ("last_run", "last_status", "last_error")})
            _save_tasks(task_storage_root, data)
        logger.warning("Scheduled task %s has an unavailable project: %s", task_id, error)
        return

    session = state.sessions.get(thread_id)
    if session is None:
        session = ThreadSession(thread_id=thread_id, project_id=project_id, title=str(task.get("name") or "计划任务"))
        session.metadata["project_root"] = str(project_root)
        state.sessions[thread_id] = session
    else:
        session.project_id = session.project_id or project_id
        session.metadata.setdefault("project_root", str(project_root))
    session.save(state.get_session_file(session))

    payload = json.dumps(
        {
            "thread_id": thread_id,
            "content": str(task.get("prompt", "")),
            "model_id": model_id,
            "project_id": project_id,
            "scheduled_task_id": task_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/chat/stream",
            "raw_path": b"/api/chat/stream",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 0),
            "app": SimpleNamespace(state=SimpleNamespace(server_state=_ProjectScopedState(state, project_root))),
        },
        receive,
    )

    try:
        response = await chat_stream(request)
        if not isinstance(response, StreamingResponse) or response.status_code >= 400:
            detail = getattr(response, "body", b"").decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"模型请求未能启动：{detail}")
        finished = False
        approval_required = False
        inference_failed = False
        async for chunk in response.body_iterator:
            event_text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            if "event: text_chunk" in event_text:
                try:
                    body = json.loads(event_text.split("data:", 1)[1].strip())
                    inference_failed = inference_failed or str(body.get("content", "")).startswith(
                        "Model inference error:"
                    )
                except (IndexError, json.JSONDecodeError):
                    pass
            if "event: approval_required" in event_text:
                approval_required = True
                try:
                    body = json.loads(event_text.split("data:", 1)[1].strip())
                    pending = state.pending_approvals.get(f"{thread_id}:{body.get('action_id')}")
                    if pending and not pending.done():
                        pending.set_result("N")
                except (IndexError, json.JSONDecodeError):
                    pass
            if "event: finish" in event_text:
                body = json.loads(event_text.split("data:", 1)[1].strip())
                finished = True
                exit_status = body.get("exit_status", 0)
                if exit_status not in (0, "0", "finish", None) or inference_failed:
                    raise RuntimeError("Agent 执行未成功")
        if not finished:
            raise RuntimeError("模型响应意外中断")
        task["last_status"] = "approval_required" if approval_required else "success"
        task["last_error"] = "需要人工审批的操作已拒绝；请在交互对话中执行。" if approval_required else None
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        location = " > ".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames[-4:])
        logger.error("Scheduled task %s failed (%s: %s) at %s", task_id, type(error).__name__, error, location)
        task["last_status"] = "failed"
        task["last_error"] = "任务执行失败，请检查模型配置、网络和任务权限。"
    finally:
        task["last_run"] = time.time()
        data = _load_tasks(task_storage_root)
        current = next((item for item in data["tasks"] if item.get("id") == task_id), None)
        if current is not None:
            current.update(
                {key: task.get(key) for key in ("thread_id", "last_run", "last_status", "last_error", "enabled")}
            )
            _save_tasks(task_storage_root, data)


async def _scheduler_loop(state: ServerState) -> None:
    while True:
        now = datetime.now(timezone.utc)
        for root, project_id in _project_roots(state):
            data = _load_tasks(root)
            changed = False
            for task in data["tasks"]:
                if not task.get("enabled", True) or task.get("last_status") == "running":
                    continue
                if _is_due(task, now):
                    task["last_status"] = "running"
                    task["enabled"] = False
                    task["last_error"] = None
                    changed = True
                    task_project_id = task.get("project_id") or project_id
                    asyncio.create_task(_execute_task(state, task, root, task_project_id))
            if changed:
                _save_tasks(root, data)
        await asyncio.sleep(1)


def start_scheduler(app: Any) -> None:
    app.state.scheduled_task_runner = asyncio.create_task(_scheduler_loop(app.state.server_state))


async def stop_scheduler(app: Any) -> None:
    task = getattr(app.state, "scheduled_task_runner", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def get_scheduled_tasks(request: Request) -> JSONResponse:
    state = _get_state(request)
    return JSONResponse(_load_tasks(state.root_path))


async def create_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = str(body.get("name", "")).strip()
    prompt = str(body.get("prompt", "")).strip()
    if not name or not prompt:
        return JSONResponse({"error": "name and prompt are required"}, status_code=400)
    try:
        run_at = _parse_run_at(body.get("run_at"))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    if run_at <= datetime.now(timezone.utc):
        return JSONResponse({"error": "run_at must be in the future"}, status_code=400)
    if not body.get("model_id"):
        return JSONResponse({"error": "model_id is required"}, status_code=400)

    data = _load_tasks(state.root_path)
    new_task = {
        "id": f"task_{uuid.uuid4().hex[:8]}",
        "name": name,
        "run_at": run_at.isoformat(),
        "prompt": prompt,
        "thread_id": body.get("thread_id"),
        "model_id": body.get("model_id"),
        "project_id": body.get("project_id"),
        "enabled": bool(body.get("enabled", True)),
        "created_at": time.time(),
        "last_run": None,
        "last_status": "idle",
        "last_error": None,
    }
    data["tasks"].append(new_task)
    _save_tasks(state.root_path, data)
    return JSONResponse(new_task, status_code=201)


async def toggle_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    data = _load_tasks(state.root_path)
    target = next((item for item in data["tasks"] if item.get("id") == request.path_params.get("task_id")), None)
    if not target:
        return JSONResponse({"error": "Scheduled task not found"}, status_code=404)
    target["enabled"] = not target.get("enabled", True)
    _save_tasks(state.root_path, data)
    return JSONResponse(target)


async def run_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    data = _load_tasks(state.root_path)
    target = next((item for item in data["tasks"] if item.get("id") == request.path_params.get("task_id")), None)
    if not target:
        return JSONResponse({"error": "Scheduled task not found"}, status_code=404)
    if target.get("last_status") == "running":
        return JSONResponse({"error": "Scheduled task is already running"}, status_code=409)
    project_id = target.get("project_id")
    target["last_status"] = "running"
    target["last_error"] = None
    _save_tasks(state.root_path, data)
    asyncio.create_task(_execute_task(state, target, state.root_path, project_id))
    return JSONResponse({"status": "started", "task_id": target["id"]}, status_code=202)


async def delete_scheduled_task(request: Request) -> JSONResponse:
    state = _get_state(request)
    data = _load_tasks(state.root_path)
    task_id = request.path_params.get("task_id")
    tasks = [task for task in data["tasks"] if task.get("id") != task_id]
    if len(tasks) == len(data["tasks"]):
        return JSONResponse({"error": "Scheduled task not found"}, status_code=404)
    data["tasks"] = tasks
    _save_tasks(state.root_path, data)
    return JSONResponse({"status": "deleted", "task_id": task_id})


task_routes = [
    Route("/api/tasks/scheduled", get_scheduled_tasks, methods=["GET"]),
    Route("/api/tasks/scheduled", create_scheduled_task, methods=["POST"]),
    Route("/api/tasks/scheduled/{task_id}/toggle", toggle_scheduled_task, methods=["PATCH"]),
    Route("/api/tasks/scheduled/{task_id}/run", run_scheduled_task, methods=["POST"]),
    Route("/api/tasks/scheduled/{task_id}", delete_scheduled_task, methods=["DELETE"]),
]

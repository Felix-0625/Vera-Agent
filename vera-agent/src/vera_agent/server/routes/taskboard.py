"""Project task board work items.

Routes: GET/POST /api/taskboard/tasks, PATCH /api/taskboard/tasks/{id},
DELETE /api/taskboard/tasks/{id} (soft archive).

Items are stored in SQLite at `<projects_config_root>/.agents/taskboard.sqlite`
and scoped by `project_id`. Updates carry a `version` for optimistic concurrency;
a linked conversation must belong to the same project.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.session.thread import ThreadSession

STATUSES = {"backlog", "todo", "in_progress", "blocked", "in_review", "done", "canceled"}
PRIORITIES = {"urgent", "high", "medium", "low", "none"}
MAX_TITLE_LENGTH = 240
MAX_DESCRIPTION_LENGTH = 20_000
MAX_LABELS = 20
MAX_LABEL_LENGTH = 48


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path(state: ServerState) -> Path:
    return state.projects_config_root / ".agents" / "taskboard.sqlite"


@contextmanager
def _connect(state: ServerState) -> Iterator[sqlite3.Connection]:
    path = _database_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                identifier TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo',
                priority TEXT NOT NULL DEFAULT 'medium',
                labels TEXT NOT NULL DEFAULT '[]',
                sort_order INTEGER NOT NULL DEFAULT 0,
                thread_id TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                archived_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS work_items_project_status_sort "
            "ON work_items(project_id, archived_at, status, sort_order, created_at)"
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "identifier": row["identifier"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "labels": json.loads(row["labels"]),
        "sort_order": row["sort_order"],
        "thread_id": row["thread_id"],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _project_exists(state: ServerState, project_id: str) -> bool:
    projects = state.load_json_config("projects_history.json", {"projects": []}).get("projects", [])
    return any(str(project.get("id")) == project_id for project in projects)


def _body_labels(value: Any) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_LABELS:
        return None
    labels: list[str] = []
    for label in value:
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > MAX_LABEL_LENGTH:
            return None
        clean = label.strip()
        if clean not in labels:
            labels.append(clean)
    return labels


def _thread_belongs_to_project(state: ServerState, thread_id: str, project_id: str) -> bool:
    """Only link a work item to a conversation owned by the same project."""
    if not thread_id or len(thread_id) > 128 or Path(thread_id).name != thread_id:
        return False

    try:
        project_root = state.get_project_root(project_id)
    except ValueError:
        return False
    session = state.sessions.get(thread_id)
    session_file = project_root / ".agents" / "sessions" / f"{thread_id}.json"
    if session is None:
        if not session_file.is_file():
            return False
        try:
            session = ThreadSession.load(session_file)
        except (OSError, ValueError, TypeError):
            return False

    cached_root = session.metadata.get("project_root")
    if cached_root and Path(cached_root).resolve() != project_root.resolve():
        return False
    owner_id = state.infer_legacy_session_project_id(session_file, session, project_id)
    return owner_id == project_id


async def list_work_items(request: Request) -> JSONResponse:
    state: ServerState = request.app.state.server_state
    project_id = request.query_params.get("project_id", "").strip()
    if not project_id:
        return JSONResponse({"error": "project_id is required"}, status_code=400)
    if not _project_exists(state, project_id):
        return JSONResponse({"error": "Project not found"}, status_code=404)
    with _connect(state) as connection:
        rows = connection.execute(
            "SELECT * FROM work_items WHERE project_id = ? AND archived_at IS NULL "
            "ORDER BY status, sort_order, created_at, id",
            (project_id,),
        ).fetchall()
    return JSONResponse({"items": [_item(row) for row in rows]})


async def create_work_item(request: Request) -> JSONResponse:
    state: ServerState = request.app.state.server_state
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Request body must be an object"}, status_code=400)

    project_id = body.get("project_id")
    if not isinstance(project_id, str):
        return JSONResponse({"error": "project_id must be a string"}, status_code=400)
    project_id = project_id.strip()
    if not project_id:
        return JSONResponse({"error": "project_id is required"}, status_code=400)
    if not _project_exists(state, project_id):
        return JSONResponse({"error": "Project not found"}, status_code=404)

    title = body.get("title")
    description = body.get("description", "")
    status = body.get("status", "todo")
    priority = body.get("priority", "medium")
    labels = _body_labels(body.get("labels"))
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE_LENGTH:
        return JSONResponse({"error": "title must contain 1 to 240 characters"}, status_code=400)
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
        return JSONResponse({"error": "description is too long or invalid"}, status_code=400)
    if not isinstance(status, str) or status not in STATUSES:
        return JSONResponse({"error": "Invalid status, priority, or labels"}, status_code=400)
    if not isinstance(priority, str) or priority not in PRIORITIES or labels is None:
        return JSONResponse({"error": "Invalid status, priority, or labels"}, status_code=400)

    item_id = uuid.uuid4().hex
    identifier = f"VA-{item_id[:12].upper()}"
    now = _now()
    with _connect(state) as connection:
        connection.execute(
            "INSERT INTO work_items "
            "(id, project_id, identifier, title, description, status, priority, labels, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                project_id,
                identifier,
                title.strip(),
                description,
                status,
                priority,
                json.dumps(labels, ensure_ascii=False),
                now,
                now,
            ),
        )
        row = connection.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
    return JSONResponse({"item": _item(row)}, status_code=201)


async def update_work_item(request: Request) -> JSONResponse:
    state: ServerState = request.app.state.server_state
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Request body must be an object"}, status_code=400)

    item_id = request.path_params.get("item_id", "")
    with _connect(state) as connection:
        current = connection.execute(
            "SELECT * FROM work_items WHERE id = ? AND archived_at IS NULL", (item_id,)
        ).fetchone()
        if current is None:
            return JSONResponse({"error": "Work item not found"}, status_code=404)

        expected_version = body.get("version")
        if (
            isinstance(expected_version, bool)
            or not isinstance(expected_version, int)
            or expected_version != current["version"]
        ):
            return JSONResponse(
                {"error": "Work item changed; refresh and retry", "item": _item(current)}, status_code=409
            )

        changes: dict[str, Any] = {}
        if "title" in body:
            title = body["title"]
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE_LENGTH:
                return JSONResponse({"error": "title must contain 1 to 240 characters"}, status_code=400)
            changes["title"] = title.strip()
        if "description" in body:
            description = body["description"]
            if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
                return JSONResponse({"error": "description is too long or invalid"}, status_code=400)
            changes["description"] = description
        if "status" in body:
            if not isinstance(body["status"], str) or body["status"] not in STATUSES:
                return JSONResponse({"error": "Invalid status"}, status_code=400)
            changes["status"] = body["status"]
        if "priority" in body:
            if not isinstance(body["priority"], str) or body["priority"] not in PRIORITIES:
                return JSONResponse({"error": "Invalid priority"}, status_code=400)
            changes["priority"] = body["priority"]
        if "labels" in body:
            labels = _body_labels(body["labels"])
            if labels is None:
                return JSONResponse({"error": "Invalid labels"}, status_code=400)
            changes["labels"] = json.dumps(labels, ensure_ascii=False)
        if "sort_order" in body:
            order = body["sort_order"]
            if isinstance(order, bool) or not isinstance(order, int):
                return JSONResponse({"error": "sort_order must be an integer"}, status_code=400)
            changes["sort_order"] = order
        if "thread_id" in body:
            thread_id = body["thread_id"]
            if thread_id is not None and (not isinstance(thread_id, str) or len(thread_id) > 128):
                return JSONResponse({"error": "Invalid thread_id"}, status_code=400)
            if thread_id is not None and not _thread_belongs_to_project(state, thread_id, current["project_id"]):
                return JSONResponse({"error": "Conversation must belong to the same project"}, status_code=400)
            changes["thread_id"] = thread_id
        if not changes:
            return JSONResponse({"error": "No supported fields to update"}, status_code=400)

        changes["updated_at"] = _now()
        changes["version"] = expected_version + 1
        assignments = ", ".join(f"{field} = ?" for field in changes)
        cursor = connection.execute(
            f"UPDATE work_items SET {assignments} WHERE id = ? AND version = ? AND archived_at IS NULL",
            (*changes.values(), item_id, expected_version),
        )
        if cursor.rowcount != 1:
            latest = connection.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
            return JSONResponse(
                {"error": "Work item changed; refresh and retry", "item": _item(latest)}, status_code=409
            )
        updated = connection.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
    return JSONResponse({"item": _item(updated)})


async def archive_work_item(request: Request) -> JSONResponse:
    state: ServerState = request.app.state.server_state
    item_id = request.path_params.get("item_id", "")
    archived_at = _now()
    with _connect(state) as connection:
        cursor = connection.execute(
            "UPDATE work_items SET archived_at = ?, updated_at = ?, version = version + 1 "
            "WHERE id = ? AND archived_at IS NULL",
            (archived_at, archived_at, item_id),
        )
    if cursor.rowcount != 1:
        return JSONResponse({"error": "Work item not found"}, status_code=404)
    return JSONResponse({"status": "archived", "id": item_id})


taskboard_routes = [
    Route("/api/taskboard/tasks", list_work_items, methods=["GET"]),
    Route("/api/taskboard/tasks", create_work_item, methods=["POST"]),
    Route("/api/taskboard/tasks/{item_id}", update_work_item, methods=["PATCH"]),
    Route("/api/taskboard/tasks/{item_id}", archive_work_item, methods=["DELETE"]),
]

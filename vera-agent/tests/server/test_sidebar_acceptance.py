"""Acceptance checks for project history and scheduled tasks in the sidebar."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from starlette.responses import StreamingResponse
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.server import state as state_module
from vera_agent.server.routes import projects as project_routes
from vera_agent.server.routes import tasks as scheduled_tasks
from vera_agent.server.routes.tasks import _is_due, _parse_run_at
from vera_agent.session.thread import ThreadSession


@pytest.fixture
def sidebar_repo(tmp_path: Path) -> Path:
    root = tmp_path / "sidebar-project"
    root.mkdir()
    (root / "README.md").write_text("sidebar acceptance", encoding="utf-8")
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    return root


def test_threads_remain_listed_and_mutable_after_switching_projects(sidebar_repo, tmp_path):
    client = TestClient(create_app(repo_root=sidebar_repo))
    project_a = client.get("/api/projects").json()["projects"][0]
    created = client.post("/api/threads", json={"title": "Project A conversation", "project_id": project_a["id"]})
    assert created.status_code == 200
    thread_id = created.json()["thread_id"]

    project_b_root = tmp_path / "project-b"
    project_b_root.mkdir()
    project_b_extra = tmp_path / "project-b-extra"
    project_b_extra.mkdir()
    bound = client.post("/api/projects/bind", json={
        "repo_root": str(project_b_root), "name": "Project B",
        "folders": [str(project_b_root), str(project_b_extra)],
    })
    assert bound.status_code == 200
    assert bound.json()["folders"] == [str(project_b_root), str(project_b_extra)]
    project_b = next(item for item in client.get("/api/projects").json()["projects"] if item["name"] == "Project B")
    assert client.get("/api/projects/current").json()["id"] == project_b["id"]

    project_b_thread = client.post("/api/threads", json={"title": "Project B conversation", "project_id": project_b["id"]})
    assert project_b_thread.status_code == 200
    project_b_thread_id = project_b_thread.json()["thread_id"]
    assert (project_b_root / ".agents" / "sessions" / f"{project_b_thread_id}.json").exists()

    listed = client.get("/api/threads").json()["threads"]
    assert any(thread["thread_id"] == thread_id and thread["project_id"] == project_a["id"] for thread in listed)
    assert any(thread["thread_id"] == project_b_thread_id and thread["project_id"] == project_b["id"] for thread in listed)
    updated = client.patch(f"/api/threads/{thread_id}", json={"title": "Renamed from Project B"})
    assert updated.status_code == 200
    saved = json.loads((sidebar_repo / ".agents" / "sessions" / f"{thread_id}.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Renamed from Project B"


def test_unbound_thread_stays_unbound_after_reloading_a_project_root_session(sidebar_repo):
    client = TestClient(create_app(repo_root=sidebar_repo))
    state = client.app.state.server_state
    project = client.get("/api/projects").json()["projects"][0]
    created = client.post("/api/threads", json={"title": "Unbound conversation"})

    assert created.status_code == 200
    thread_id = created.json()["thread_id"]
    session_file = Path(project["path"]) / ".agents" / "sessions" / f"{thread_id}.json"
    assert session_file.exists()
    assert ThreadSession.load(session_file).project_id is None

    # Simulate a process restart: the server must preserve an explicit null binding.
    state.sessions.clear()
    reloaded = state.get_or_create_session(thread_id)
    assert reloaded.project_id is None

    state.sessions.clear()
    listed = client.get("/api/threads").json()["threads"]
    thread = next(item for item in listed if item["thread_id"] == thread_id)
    assert thread["project_id"] is None


def test_legacy_thread_without_project_id_still_infers_its_project(sidebar_repo):
    client = TestClient(create_app(repo_root=sidebar_repo))
    project = client.get("/api/projects").json()["projects"][0]
    session_dir = Path(project["path"]) / ".agents" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "th_legacy_sidebar.json"
    session_file.write_text(json.dumps({
        "thread_id": "th_legacy_sidebar", "role": "main", "title": "Legacy conversation",
    }), encoding="utf-8")

    listed = client.get("/api/threads").json()["threads"]
    legacy = next(item for item in listed if item["thread_id"] == "th_legacy_sidebar")
    assert legacy["project_id"] == project["id"]


def test_fixed_time_schedule_requires_timezone_and_is_one_time():
    due_time = datetime(2026, 10, 13, 12, 34, tzinfo=timezone.utc)
    assert _parse_run_at("2026-10-13T20:34:00+08:00") == due_time
    with pytest.raises(ValueError, match="timezone"):
        _parse_run_at("2026-10-13T20:34:00")
    task = {"run_at": due_time.isoformat(), "enabled": True, "last_status": "idle"}
    assert _is_due(task, due_time)
    task["last_status"] = "success"
    assert not _is_due(task, due_time + timedelta(days=1))
    legacy_task = {"cron": "0 9 * * *", "enabled": True, "last_status": "idle"}
    assert not _is_due(legacy_task, due_time + timedelta(days=1))


def test_task_creation_rejects_invalid_time_and_persists_execution_model(sidebar_repo):
    client = TestClient(create_app(repo_root=sidebar_repo))
    invalid = client.post("/api/tasks/scheduled", json={"name": "bad", "run_at": "tomorrow", "prompt": "do work", "model_id": "model-test"})
    assert invalid.status_code == 400

    created = client.post("/api/tasks/scheduled", json={
        "name": "fixed-time check", "run_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "prompt": "summarize the repository",
        "model_id": "model-test", "project_id": client.get("/api/projects").json()["projects"][0]["id"],
    })
    assert created.status_code == 201
    assert created.json()["model_id"] == "model-test"
    assert created.json()["project_id"] is not None


def test_project_folder_picker_distinguishes_cancel_from_failure(sidebar_repo, monkeypatch):
    client = TestClient(create_app(repo_root=sidebar_repo))
    monkeypatch.setattr(project_routes, "_choose_directory", lambda: None)
    cancelled = client.post("/api/projects/select-folder")
    assert cancelled.status_code == 200
    assert cancelled.json() == {"path": None}

    def fail_picker():
        raise RuntimeError("picker unavailable")

    monkeypatch.setattr(project_routes, "_choose_directory", fail_picker)
    failed = client.post("/api/projects/select-folder")
    assert failed.status_code == 500
    assert "无法打开本地文件夹选择器" in failed.json()["error"]


def test_scheduler_dispatches_due_fixed_time_task_once(sidebar_repo, monkeypatch):
    state = state_module.ServerState(repo_root=sidebar_repo)
    scheduled_minute = datetime(2026, 10, 13, 12, 34, tzinfo=timezone.utc)
    project_id = state.load_json_config("projects_history.json", {"projects": []})["projects"][0]["id"]
    scheduled_tasks._save_tasks(sidebar_repo, {"tasks": [{
        "id": "task_dispatch", "name": "dispatch check", "run_at": scheduled_minute.isoformat(),
        "prompt": "safe test", "model_id": "model-test", "project_id": project_id,
        "enabled": True, "last_status": "idle",
    }]})
    dispatched = asyncio.Event()

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return scheduled_minute

    async def fake_execute(_state, task, _root, _project_id):
        assert task["id"] == "task_dispatch"
        dispatched.set()

    monkeypatch.setattr(scheduled_tasks, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduled_tasks, "_project_roots", lambda _state: [(sidebar_repo, project_id)])
    monkeypatch.setattr(scheduled_tasks, "_execute_task", fake_execute)

    async def exercise():
        runner = asyncio.create_task(scheduled_tasks._scheduler_loop(state))
        try:
            await asyncio.wait_for(dispatched.wait(), timeout=1)
        finally:
            runner.cancel()
            try:
                await runner
            except asyncio.CancelledError:
                pass

    asyncio.run(exercise())
    saved = scheduled_tasks._load_tasks(sidebar_repo)["tasks"][0]
    assert saved["last_status"] == "running"
    assert saved["enabled"] is False


def test_scheduled_task_uses_bound_project_but_saves_task_state_in_app_config(tmp_path, monkeypatch):
    app_root = tmp_path / "app-config"
    app_root.mkdir()
    project_root = tmp_path / "bound-project"
    project_root.mkdir()
    state = state_module.ServerState(repo_root=app_root)
    project_id = "proj_bound"
    history = state.load_json_config("projects_history.json", {"projects": []})
    history["projects"].append({"id": project_id, "name": "Bound project", "path": str(project_root)})
    state.save_json_config("projects_history.json", history)
    task = {"id": "task_project_scope", "name": "project scope", "prompt": "check project root", "model_id": "model-test"}
    scheduled_tasks._save_tasks(app_root, {"tasks": [task]})
    observed_project_roots = []

    async def fake_chat_stream(request):
        scoped_state = request.app.state.server_state
        observed_project_roots.append(scoped_state.root_path)
        return StreamingResponse(iter([b'event: finish\ndata: {"exit_status":"finish"}\n\n']))

    from vera_agent.server.routes import chat
    monkeypatch.setattr(chat, "chat_stream", fake_chat_stream)
    asyncio.run(scheduled_tasks._execute_task(state, task, app_root, project_id))

    assert observed_project_roots == [project_root]
    assert (project_root / ".agents" / "sessions" / f"{task['thread_id']}.json").exists()
    persisted_task = scheduled_tasks._load_tasks(app_root)["tasks"][0]
    assert persisted_task["last_status"] == "success"
    assert persisted_task["thread_id"] == task["thread_id"]


@pytest.mark.skipif(not os.environ.get("VERA_TEST_DEEPSEEK_KEY"), reason="temporary DeepSeek credential not provided")
def test_scheduled_task_executes_through_real_deepseek_model(sidebar_repo, monkeypatch, request):
    key = os.environ["VERA_TEST_DEEPSEEK_KEY"]
    config_dir = sidebar_repo / ".agents"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "models_config.json"
    request.addfinalizer(lambda: config_path.unlink(missing_ok=True))
    config_path.write_text(json.dumps({"models": [{
        "id": "temporary-deepseek-flash", "name": "deepseek-flash", "provider": "deepseek",
        "api_key": key, "enabled": True, "temperature": 0,
    }]}), encoding="utf-8")
    monkeypatch.setenv("VERA_TEST_DEEPSEEK_KEY", "")

    with TestClient(create_app(repo_root=sidebar_repo)) as client:
        project_id = client.get("/api/projects").json()["projects"][0]["id"]
        created = client.post("/api/tasks/scheduled", json={
            "name": "temporary model acceptance", "run_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "prompt": "请只回复 DONE，不要调用任何工具。", "model_id": "temporary-deepseek-flash",
            "project_id": project_id,
        })
        assert created.status_code == 201
        task_id = created.json()["id"]
        started = client.post(f"/api/tasks/scheduled/{task_id}/run")
        assert started.status_code == 202

        deadline = time.monotonic() + 90
        result = None
        while time.monotonic() < deadline:
            tasks = client.get("/api/tasks/scheduled").json()["tasks"]
            result = next(task for task in tasks if task["id"] == task_id)
            if result["last_status"] != "running":
                break
            time.sleep(1)

        assert result["last_status"] == "success", result.get("last_error")
        assert result["thread_id"]
        messages = client.get(f"/api/threads/{result['thread_id']}/messages").json()["messages"]
        assert any(message.get("role") == "assistant" and str(message.get("content", "")).strip() and "Model inference error" not in str(message.get("content", "")) for message in messages)
        client.delete(f"/api/tasks/scheduled/{task_id}")
    config_path.unlink(missing_ok=True)

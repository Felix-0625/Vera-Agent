"""Scheduled tasks run through the real chat pipeline with application-scoped model settings."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.routes import tasks as scheduled_tasks
from vera_agent.server.state import ServerState


def test_scheduled_task_uses_application_models_for_a_separate_project(tmp_path: Path):
    app_root = tmp_path / "app-data"
    project = tmp_path / "project"
    project.mkdir()
    (app_root / ".agents").mkdir(parents=True)
    (app_root / ".agents" / "models_config.json").write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "scheduled-model",
                        "name": "deepseek/deepseek-chat",
                        "provider": "deepseek",
                        "api_key": "test-only",
                        "base_url": "https://api.deepseek.com",
                        "enabled": True,
                        "is_default": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    state = ServerState(repo_root=app_root)
    state.init_workspace(project, project_id="proj-scheduled", project_name="Scheduled project")
    task = {"id": "task_real", "name": "check", "prompt": "Say done.", "model_id": "scheduled-model"}
    scheduled_tasks._save_tasks(project, {"tasks": [dict(task)]})

    def fake_query_stream(_model, _messages, _tools=None, *, on_text, **_kwargs):
        on_text("SCHEDULED_DONE")
        return {"role": "assistant", "content": "SCHEDULED_DONE", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        asyncio.run(scheduled_tasks._execute_task(state, task, project, "proj-scheduled"))

    stored = scheduled_tasks._load_tasks(project)["tasks"][0]
    assert stored["last_status"] == "success", stored
    assert stored["last_error"] is None
    session = json.loads((project / ".agents" / "sessions" / f"{stored['thread_id']}.json").read_text(encoding="utf-8"))
    assert any(message.get("content") == "SCHEDULED_DONE" for message in session["messages"])


def _setup(tmp_path: Path, extra_task: dict | None = None):
    app_root = tmp_path / "app-data"
    project = tmp_path / "project"
    project.mkdir()
    (app_root / ".agents").mkdir(parents=True)
    (app_root / ".agents" / "models_config.json").write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "scheduled-model",
                        "name": "deepseek/deepseek-chat",
                        "provider": "deepseek",
                        "api_key": "test-only",
                        "base_url": "https://api.deepseek.com",
                        "enabled": True,
                        "is_default": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    state = ServerState(repo_root=app_root)
    state.init_workspace(project, project_id="proj-scheduled", project_name="Scheduled project")
    task = {"id": "task_x", "name": "check", "prompt": "Do it.", "model_id": "scheduled-model", **(extra_task or {})}
    scheduled_tasks._save_tasks(project, {"tasks": [dict(task)]})
    return state, project, task


def _stored(project: Path) -> dict:
    return scheduled_tasks._load_tasks(project)["tasks"][0]


def test_a_task_without_a_model_fails_before_any_model_call(tmp_path: Path):
    state, project, task = _setup(tmp_path, {"model_id": None})

    asyncio.run(scheduled_tasks._execute_task(state, task, project, "proj-scheduled"))

    stored = _stored(project)
    assert stored["last_status"] == "failed" and "没有指定模型" in stored["last_error"] and stored["last_run"]


def test_a_task_bound_to_a_missing_project_fails_with_a_rebind_hint(tmp_path: Path):
    state, project, task = _setup(tmp_path)

    asyncio.run(scheduled_tasks._execute_task(state, task, project, "no-such-project"))

    stored = _stored(project)
    assert stored["last_status"] == "failed" and "重新绑定项目" in stored["last_error"]


def test_a_model_error_marks_the_task_failed_without_leaking_details(tmp_path: Path):
    state, project, task = _setup(tmp_path)

    def broken(*_args, **_kwargs):
        raise RuntimeError("secret upstream detail")

    with patch.object(LitellmModel, "query_stream", new=broken):
        asyncio.run(scheduled_tasks._execute_task(state, task, project, "proj-scheduled"))

    stored = _stored(project)
    assert stored["last_status"] == "failed"
    assert "secret upstream detail" not in stored["last_error"] and "任务执行失败" in stored["last_error"]
    assert stored["thread_id"].startswith("th_scheduled_") and stored["last_run"]


def test_an_existing_thread_is_reused_and_receives_the_answer(tmp_path: Path):
    state, project, task = _setup(tmp_path, {"thread_id": "th_existing"})

    def fake_query_stream(_model, _messages, _tools=None, *, on_text, **_kwargs):
        on_text("REUSED")
        return {"role": "assistant", "content": "REUSED", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        asyncio.run(scheduled_tasks._execute_task(state, task, project, "proj-scheduled"))

    assert _stored(project)["thread_id"] == "th_existing" and _stored(project)["last_status"] == "success"
    session = json.loads((project / ".agents" / "sessions" / "th_existing.json").read_text(encoding="utf-8"))
    assert any(message.get("content") == "REUSED" for message in session["messages"])

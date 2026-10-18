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

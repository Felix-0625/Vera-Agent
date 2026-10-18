"""User-controlled text with template syntax must reach the model literally and never break a chat turn."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from starlette.testclient import TestClient

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app
from vera_agent.server.routes.chat import _fill_context_placeholders


def _write_model(root: Path) -> None:
    config = root / ".agents" / "models_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "test-chat-model",
                        "name": "deepseek/deepseek-chat",
                        "provider": "deepseek",
                        "api_key": "test-only",
                        "base_url": "https://api.deepseek.com",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_fill_context_placeholders_is_single_pass_and_literal():
    prompt = "A {{user_rules_context}} B {{project_instructions_context}} C {{ other }}"
    values = {
        "user_rules_context": "rule mentions {{project_instructions_context}}",
        "project_instructions_context": "P",
    }
    assert _fill_context_placeholders(prompt, values) == (
        "A rule mentions {{project_instructions_context}} B P C {{ other }}"
    )


def test_template_syntax_in_goal_rules_and_node_prompt_does_not_break_the_turn(tmp_path: Path):
    client = TestClient(create_app(repo_root=tmp_path))
    _write_model(tmp_path)
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    client.post("/api/settings/rules", json={"content": "Keep {{ braces }} and {% raw %} as text."})

    group = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": "architecture",
            "name": "Template syntax fixture",
            "goal": "Ship feature GOAL_MARKER with {{ literal }} braces",
            "nodes": [
                {
                    "id": "lead",
                    "type": "agent",
                    "title": "Lead",
                    "role": "lead",
                    "prompt_template": "Project goal: {{goal}}\nTask: {{input}}\nNote {% if x %}stays{% endif %}",
                }
            ],
            "edges": [],
        },
    ).json()["group"]
    run = client.post(
        f"/api/groups/{group['group_id']}/runs",
        json={"project_id": project_id, "confirmation": "Y", "input": "Plan the work"},
    ).json()["run"]
    observed: dict[str, Any] = {}

    def fake_query_stream(_model, messages, _tools=None, *, on_text, **_kwargs):
        observed["system"] = str(messages[0]["content"])
        on_text("DONE")
        return {"role": "assistant", "content": "DONE", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        response = client.post(
            "/api/chat/stream",
            json={
                "thread_id": run["sessions"][0]["thread_id"],
                "project_id": project_id,
                "group_id": group["group_id"],
                "content": "Start",
                "model_id": "test-chat-model",
                "workflow_input": "Plan the work",
            },
        )

    assert response.status_code == 200
    assert "event: finish" in response.text
    assert "Model inference error" not in response.text, response.text
    system = observed["system"]
    assert "Project goal: Ship feature GOAL_MARKER with {{ literal }} braces" in system
    assert "Keep {{ braces }} and {% raw %} as text." in system
    assert "{% if x %}stays{% endif %}" in system


def test_attached_skill_instructions_reach_the_system_prompt(tmp_path: Path):
    client = TestClient(create_app(repo_root=tmp_path))
    _write_model(tmp_path)
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    installed = client.post(
        "/api/skills/install",
        json={"name": "marker", "description": "test", "instructions": "First line must be SKILL_MARKER {{ x }}."},
    )
    assert installed.status_code == 200, installed.text
    observed: dict[str, Any] = {}

    def fake_query_stream(_model, messages, _tools=None, *, on_text, **_kwargs):
        observed["system"] = str(messages[0]["content"])
        on_text("ok")
        return {"role": "assistant", "content": "ok", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        response = client.post(
            "/api/chat/stream",
            json={
                "project_id": project_id,
                "model_id": "test-chat-model",
                "attached_skills": ["marker"],
                "content": "hi",
            },
        )
    assert response.status_code == 200
    assert "<skill name='marker'>" in observed["system"]
    assert "First line must be SKILL_MARKER {{ x }}." in observed["system"]

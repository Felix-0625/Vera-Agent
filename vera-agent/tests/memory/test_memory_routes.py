"""Memory panel routes and recall inside a real chat turn."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from tests.chat_helpers import TEST_MODEL_ID, make_chat_repo
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app


def test_memory_crud_history_and_restore(tmp_path: Path):
    client = TestClient(create_app(repo_root=make_chat_repo(tmp_path / "repo")))
    created = client.post("/api/memories", json={"scope": "user", "kind": "preference", "content": "回答用中文"})
    assert created.status_code == 201
    memory_id = created.json()["memory"]["memory_id"]
    assert client.patch(f"/api/memories/{memory_id}", json={"content": "回答用英文"}).status_code == 200
    assert client.delete(f"/api/memories/{memory_id}").status_code == 200
    assert client.get("/api/memories").json()["memories"] == []
    assert client.get("/api/memories", params={"status": "deleted"}).json()["memories"][0]["memory_id"] == memory_id
    history = client.get(f"/api/memories/{memory_id}/history").json()["history"]
    assert [entry["actor"] for entry in history] == ["user", "user", "user"]
    restored = client.post(f"/api/memories/{memory_id}/restore", json={"version": 1}).json()["memory"]
    assert restored["content"] == "回答用中文" and restored["status"] == "active"
    rejected = client.post("/api/memories", json={"scope": "user", "kind": "fact", "content": "password=hunter2"})
    assert rejected.status_code == 400
    # The legacy settings API sees the same user-scope memory.
    assert client.get("/api/settings/user-memories").json()["memories"][0]["id"] == memory_id


def test_settings_validate_and_default_consolidation_off(tmp_path: Path):
    client = TestClient(create_app(repo_root=make_chat_repo(tmp_path / "repo")))
    assert client.get("/api/settings/memory").json()["consolidation"] == "off"
    updated = client.put("/api/settings/memory", json={"consolidation": "every_word", "token_budget": 5}).json()
    assert updated["consolidation"] == "off" and updated["token_budget"] == 40


def test_relevant_memory_and_rules_reach_the_system_prompt(tmp_path: Path):
    client = TestClient(create_app(repo_root=make_chat_repo(tmp_path / "repo")))
    client.post("/api/memories", json={"scope": "user", "kind": "rule", "content": "修改代码后必须运行测试。"})
    client.post("/api/memories", json={"scope": "user", "kind": "fact", "content": "数据库迁移脚本放在 db/migrations"})
    seen: list[str] = []

    def capture(_model, messages, tools=None, *, on_text, **_kwargs):
        seen.append(str(messages[0]["content"]))
        return {"role": "assistant", "content": "ok", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=capture):
        client.post(
            "/api/chat/stream", json={"thread_id": "th_m", "model_id": TEST_MODEL_ID, "content": "新增一个数据库迁移"}
        )
    assert "<runtime_memory>" in seen[0]
    assert "修改代码后必须运行测试。" in seen[0] and "db/migrations" in seen[0]

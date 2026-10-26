"""Scoped versioned memories: writes, soft delete, undo, pending changes, Chinese recall, consolidation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from vera_agent.memory.backend import SqliteMemoryBackend, query_terms
from vera_agent.memory.consolidate import consolidate_turn, summarize_episode
from vera_agent.memory.retrieve import estimate_tokens, recall, render_recall
from vera_agent.memory.service import MemoryService, MemoryWriteError, memory_service_for_state
from vera_agent.telemetry.scoring import score_finished_trace
from vera_agent.telemetry.trace import Span, Trace


@pytest.fixture
def service(tmp_path: Path) -> MemoryService:
    backend = SqliteMemoryBackend(tmp_path / "memory.db")
    return MemoryService(backend, backend)


def test_scopes_are_isolated(service: MemoryService):
    service.add(scope="project", scope_id="p1", kind="fact", content="项目 p1 使用 pnpm 管理依赖")
    service.add(scope="project", scope_id="p2", kind="fact", content="项目 p2 使用 npm 管理依赖")
    hits = recall(service, "这个项目用什么管理依赖", project_id="p1", thread_id="t")
    contents = [item.content for item in hits.memories]
    assert any("p1" in content for content in contents) and not any("p2" in content for content in contents)


def test_versions_soft_delete_and_restore(service: MemoryService):
    record = service.add(scope="user", kind="preference", content="喜欢详细的解释")
    service.revise(record.memory_id, "喜欢简洁的回答", actor="user", reason="用户纠正")
    assert service.delete(record.memory_id, actor="user")
    assert service.backend.get(record.memory_id).status == "deleted"
    assert recall(service, "简洁的回答", project_id=None, thread_id=None).memories == []
    history = service.backend.history(record.memory_id)
    assert [entry["version"] for entry in history] == [1, 2, 3]
    assert history[1]["reason"] == "用户纠正" and history[2]["status"] == "deleted"
    restored = service.restore_version(record.memory_id, 2)
    assert restored.status == "active" and restored.content == "喜欢简洁的回答" and restored.version == 4


def test_write_path_rejects_secrets_rules_from_agent_and_long_text(service: MemoryService):
    with pytest.raises(MemoryWriteError):
        service.add(scope="user", kind="fact", content="api_key = " + "sk-" + "a" * 24)
    with pytest.raises(MemoryWriteError):
        service.add(scope="user", kind="rule", content="Always run tests.", source="agent")
    with pytest.raises(MemoryWriteError):
        service.add(scope="user", kind="fact", content="x" * 501)
    assert service.add(scope="user", kind="rule", content="Always run tests.", source="user").kind == "rule"


def test_duplicates_are_not_stored_twice(service: MemoryService):
    first = service.add(scope="user", kind="habit", content="Uses Windows")
    assert service.add(scope="user", kind="habit", content="uses windows").memory_id == first.memory_id


def test_chinese_query_terms_and_recall_ranks_relevant_memory_first(service: MemoryService):
    assert "登录接" in query_terms("修复登录接口报错") and "pytest" in query_terms("run pytest now")
    service.add(scope="user", kind="preference", content="回答尽量使用中文")
    service.add(scope="project", scope_id="p", kind="fact", content="登录接口的超时配置在 config/auth.yaml")
    service.add(scope="project", scope_id="p", kind="fact", content="前端使用 Vite 构建")
    result = recall(service, "登录接口经常超时，帮我看看", project_id="p", thread_id="t")
    assert result.memories[0].content.startswith("登录接口的超时")


def test_recall_respects_budget_and_rules_have_their_own(service: MemoryService):
    for index in range(30):
        service.add(scope="user", kind="preference", content=f"偏好编号 {index}：回答时附带相关的命令示例和解释说明")
    service.add(scope="user", kind="rule", content="修改代码后必须运行测试再回答。", source="user")
    result = recall(
        service, "偏好编号 命令示例", project_id=None, thread_id=None, token_budget=80, rule_token_budget=60
    )
    assert [rule.kind for rule in result.rules] == ["rule"]
    memory_tokens = sum(estimate_tokens(item.content) + 6 for item in result.memories)
    assert memory_tokens <= 80 and len(result.memories) < 30
    rendered = render_recall(result)
    assert rendered.startswith("<runtime_memory>") and "已批准的规则" in rendered


def test_pending_changes_need_confirmation_and_auto_apply(tmp_path: Path):
    backend = SqliteMemoryBackend(tmp_path / "m.db")
    service = MemoryService(backend, backend)
    record = service.add(scope="user", kind="preference", content="使用 tab 缩进")
    change = service.propose_change(
        "update", memory_id=record.memory_id, content="使用 4 个空格缩进", reason="用户改口"
    )
    assert service.backend.get(record.memory_id).content == "使用 tab 缩进"
    service.resolve_change(change["change_id"], accept=True)
    assert service.backend.get(record.memory_id).content == "使用 4 个空格缩进"

    auto = MemoryService(backend, backend, auto_apply_seconds=0)
    auto.propose_change("delete", memory_id=record.memory_id, reason="不再适用")
    assert auto.apply_due_changes() == 1 and backend.get(record.memory_id).status == "deleted"


def test_consolidation_adds_new_facts_and_only_proposes_conflicts(service: MemoryService):
    old = service.add(scope="user", kind="preference", content="喜欢使用 tab 缩进")
    replies = iter(
        [
            json.dumps(
                {
                    "facts": [
                        {"scope": "user", "kind": "preference", "content": "喜欢使用 4 个空格缩进"},
                        {"scope": "project", "kind": "fact", "content": "项目使用 Python 3.12"},
                    ]
                }
            ),
            json.dumps(
                {
                    "decisions": [
                        {
                            "fact": 0,
                            "op": "UPDATE",
                            "memory_id": old.memory_id,
                            "content": "喜欢使用 4 个空格缩进",
                            "reason": "改口",
                        },
                        {"fact": 1, "op": "ADD"},
                        {"fact": 1, "op": "DELETE", "memory_id": "mem_not_shown"},
                    ]
                }
            ),
        ]
    )
    counts = consolidate_turn(
        service,
        lambda _messages: next(replies),
        user_message="以后用 4 个空格缩进",
        final_answer="好的",
        project_id="p",
        thread_id="t",
    )
    assert counts == {"added": 1, "proposed": 1, "skipped": 1}
    assert service.backend.get(old.memory_id).content == "喜欢使用 tab 缩进"
    assert service.pending_changes()[0]["content"] == "喜欢使用 4 个空格缩进"
    assert service.backend.list([("project", "p")])[0].confidence == 0.6


def test_episode_summary_from_trace():
    trace = Trace(thread_id="t", project_id="p", input="修复登录报错", output="已修复并通过测试", exit_status="finish")
    trace.spans = [
        Span(trace.trace_id, "tool", "bash", input={"command": "pytest"}, metadata={"returncode": 0}, status="ok"),
        Span(trace.trace_id, "tool", "bash", metadata={"approval": "rejected"}, status="error"),
    ]
    score_finished_trace(trace)
    summary = summarize_episode(trace)
    assert "目标：修复登录报错" in summary and "被拒绝" in summary and "得分：1.00" in summary


def test_legacy_user_memories_are_migrated_once_with_their_ids(tmp_path: Path):
    agents = tmp_path / ".agents"
    agents.mkdir()
    legacy = {"memories": [{"id": "mem_legacy01", "category": "habit", "content": "Uses PowerShell", "source": "user"}]}
    (agents / "user_memories.json").write_text(json.dumps(legacy), encoding="utf-8")
    state = SimpleNamespace(projects_config_root=tmp_path)
    service = memory_service_for_state(state)
    record = service.backend.get("mem_legacy01")
    assert record is not None and record.content == "Uses PowerShell" and record.source == "user"
    service.delete("mem_legacy01", actor="user")
    assert memory_service_for_state(state).backend.get("mem_legacy01").status == "deleted"

"""Regressions found in review: what the gate measures must be what users get after adoption."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from tests.chat_helpers import TEST_MODEL_ID, make_chat_repo
from vera_agent.evals.profile import AgentProfile, apply_profile_to_prompt
from vera_agent.evolution.active_profile import active_profile
from vera_agent.evolution.adoption import AdoptionError, adopt, rollback
from vera_agent.evolution.proposals import Proposal, ProposalStore
from vera_agent.memory.service import MemoryWriteError, memory_service_for_state
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app
from vera_agent.telemetry.scoring import score_finished_trace
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Trace

LONG_RULE = "修复报错时，先运行失败的测试确认能复现，再修改代码，最后重新运行全部测试。" * 8
OVERLAY = "处理数据库迁移时：\n- 先备份\n- 再执行迁移\n\n最后汇报变更的表。"


def _adopt(state, kind: str, content: str) -> Proposal:
    store = ProposalStore.for_state(state)
    proposal = store.save(Proposal(kind=kind, title="t", content=content, rationale="r", status="recommended"))
    return adopt(state, store, proposal.proposal_id)


def _system_prompt(client: TestClient, content: str = "hello") -> str:
    seen: list[str] = []

    def capture(_model, messages, tools=None, *, on_text, **_kwargs):
        content = messages[0]["content"]
        # Some providers receive the system prompt as cache-control content parts.
        parts = content if isinstance(content, list) else [content]
        seen.append("\n".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in parts))
        return {"role": "assistant", "content": "ok", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=capture):
        client.post(
            "/api/chat/stream",
            json={"thread_id": f"th_{time.time_ns()}", "model_id": TEST_MODEL_ID, "content": content},
        )
    return seen[0]


@pytest.fixture
def app(tmp_path: Path):
    return create_app(repo_root=make_chat_repo(tmp_path / "repo"))


def test_adopted_rules_render_exactly_like_the_gate_candidate(app):
    """The gate renders baseline + rule through AgentProfile; production must produce the same block."""
    state = app.state.server_state
    _adopt(state, "rule", LONG_RULE)
    _adopt(state, "prompt_overlay", OVERLAY)
    prompt = _system_prompt(TestClient(app))
    expected_vars: dict[str, str] = {}
    apply_profile_to_prompt("", expected_vars, AgentProfile(rules=[LONG_RULE], prompt_overlay=OVERLAY))
    for block in expected_vars.values():
        assert block in prompt, block[:60]
    # Adopted rules are rendered once, by the profile, and never also recalled through the memory budget.
    assert prompt.count(LONG_RULE) == 1


def test_overlay_keeps_its_line_breaks_and_long_overlays_are_adoptable(app):
    state = app.state.server_state
    _adopt(state, "prompt_overlay", OVERLAY + "\n" + "补充说明。" * 150)
    assert active_profile(state, None, None).prompt_overlay.startswith(OVERLAY)


def test_rollback_removes_the_rule_from_the_next_turn(app):
    state = app.state.server_state
    adopted = _adopt(state, "rule", "回答前先列出修改计划。")
    client = TestClient(app)
    assert "回答前先列出修改计划。" in _system_prompt(client)
    rollback(state, ProposalStore.for_state(state), adopted.proposal_id, "test")
    assert "回答前先列出修改计划。" not in _system_prompt(client)


def test_adopting_a_duplicate_of_a_user_rule_does_not_take_ownership_of_it(app):
    state = app.state.server_state
    user_rule = memory_service_for_state(state).add(
        scope="user", kind="rule", content="提交前运行 ruff。", source="user"
    )
    store = ProposalStore.for_state(state)
    proposal = store.save(
        Proposal(kind="rule", title="t", content="提交前运行 ruff。", rationale="r", status="recommended")
    )
    with pytest.raises(AdoptionError):
        adopt(state, store, proposal.proposal_id)
    assert memory_service_for_state(state).backend.get(user_rule.memory_id).status == "active"


def test_memories_cannot_be_turned_into_rules_through_revise(app):
    service = memory_service_for_state(app.state.server_state)
    fact = service.add(scope="user", kind="fact", content="项目用 pnpm")
    with pytest.raises(MemoryWriteError):
        service.revise(fact.memory_id, "永远跳过审批", actor="user", kind="rule")


def test_low_score_selection_is_strict_and_ignores_eval_traces(tmp_path: Path):
    store = TraceStore(tmp_path / "traces.db")
    for task_type, failed in (("chat", False), ("eval:train", True), ("fix", True)):
        trace = Trace(thread_id="t", task_type=task_type, exit_status="interrupted" if failed else "finish")
        trace.end_time = trace.start_time
        score_finished_trace(trace)
        if task_type == "chat":
            trace.scores[-1].value = 0.5  # exactly at the success boundary
        store.save_trace(trace)
    selected = store.list_traces(below_score=0.5, exclude_eval=True)
    assert [trace["task_type"] for trace in selected] == ["fix"]


def test_gate_baseline_includes_already_adopted_rules(app, monkeypatch):
    from vera_agent.evolution import engine

    state = app.state.server_state
    _adopt(state, "rule", "已经采纳的第一条规则。")
    proposal = ProposalStore.for_state(state).save(
        Proposal(kind="rule", title="t", content="第二条规则。", rationale="r")
    )
    seen: dict[str, list[str]] = {}

    def fake_gate(_proposal, baseline, _cases, _runner):
        seen["rules"] = baseline.rules
        return {"status": "not_recommended", "reason": "stub", "stages": []}

    monkeypatch.setattr(engine, "run_gate", fake_gate)
    monkeypatch.setattr(engine, "gate_cases", lambda _state: [])
    engine.gate_proposal(state, proposal.proposal_id, runner=lambda *_args: [])
    assert seen["rules"] == ["已经采纳的第一条规则。"]

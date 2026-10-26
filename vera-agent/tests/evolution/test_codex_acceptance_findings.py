"""Regressions for the 5 defects found in the 2026-10-25 Codex acceptance review.

Each test fails on the pre-fix code and passes after it; see the review report for the original
reproduction commands and trace excerpts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vera_agent.evolution.active_profile import active_profile
from vera_agent.evolution.adoption import AdoptionError, adopt, rollback
from vera_agent.evolution.monitor import check_adoptions
from vera_agent.evolution.proposals import Proposal, ProposalStore
from vera_agent.memory.backend import SqliteMemoryBackend
from vera_agent.memory.service import MemoryService, memory_service_for_state
from vera_agent.telemetry.scoring import is_verification_command, score_finished_trace
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Span, Trace

# --- round 2: Codex recheck of the round-1 fixes (2026-10-25) ---------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python -m unittest.mock", False),  # a different module, not the test runner
        ("python -m unittest -q", True),
        ("python -m pytest --version", False),  # asks the tool about itself, runs no tests
        ("ruff --version", False),
        ("  npm test", True),  # leading whitespace must not shift the subcommand check
        ("\tgo build ./...", True),
    ],
)
def test_is_verification_command_round_2(command: str, expected: bool):
    assert is_verification_command(command) is expected


@pytest.mark.parametrize(
    "command",
    [
        "python -m pytest -q --version",  # the info flag is not the first argument
        "python -m pytest --version -q",
        "pytest -q -V",
    ],
)
def test_an_info_flag_anywhere_in_the_arguments_is_not_verification(command: str):
    assert is_verification_command(command) is False


def test_pytest_version_after_a_pytest_q_does_not_overwrite_a_failed_run():
    """python -m pytest -q --version exits 0 without running anything; it must not read as a pass."""
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [
        Span(
            trace.trace_id,
            "tool",
            "bash",
            input={"command": "python -m pytest -q"},
            metadata={"returncode": 1},
            status="error",
        ),
        Span(
            trace.trace_id,
            "tool",
            "bash",
            input={"command": "python -m pytest -q --version"},
            metadata={"returncode": 0},
            status="ok",
        ),
    ]
    scores = {score.name: score.value for score in score_finished_trace(trace)}
    assert scores["verification"] == 0.0 and scores["outcome"] == 0.0


def test_leading_whitespace_does_not_hide_a_failing_verification():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [
        Span(
            trace.trace_id, "tool", "bash", input={"command": "  npm test"}, metadata={"returncode": 1}, status="error"
        )
    ]
    scores = {score.name: score.value for score in score_finished_trace(trace)}
    assert scores["verification"] == 0.0 and scores["outcome"] == 0.0


def test_overlay_trailing_spaces_and_blank_line_count_survive_normalization():
    from vera_agent.memory.service import normalize_content

    text = "line one  \n\n\n\nline two"
    assert normalize_content(text, "rule") == text


def test_duplicate_rule_in_different_project_scopes_adopts_independently(tmp_path: Path):
    from types import SimpleNamespace

    state = SimpleNamespace(projects_config_root=tmp_path, skill_mgr=None)
    store = ProposalStore.for_state(state)
    p1 = store.save(
        Proposal(
            kind="rule",
            title="a",
            content="同样的规则。",
            rationale="r",
            scope="project",
            scope_id="p1",
            status="recommended",
        )
    )
    p2 = store.save(
        Proposal(
            kind="rule",
            title="b",
            content="同样的规则。",
            rationale="r",
            scope="project",
            scope_id="p2",
            status="recommended",
        )
    )
    adopt(state, store, p1.proposal_id)
    adopted_p2 = adopt(state, store, p2.proposal_id)  # must not raise: different scope, different memory
    assert active_profile(state, "p1", None).rules == ["同样的规则。"]
    assert active_profile(state, "p2", None).rules == ["同样的规则。"]
    rollback(state, store, p1.proposal_id, "test")
    assert active_profile(state, "p1", None).rules == []
    assert active_profile(state, "p2", None).rules == ["同样的规则。"]
    assert store.get(p2.proposal_id).status == "adopted"
    assert adopted_p2.adoption["memory_id"] != store.get(p1.proposal_id).adoption["memory_id"]


def test_mixed_short_and_long_chinese_terms_are_both_searched(tmp_path: Path):
    backend = SqliteMemoryBackend(tmp_path / "m.db")
    service = MemoryService(backend, backend)
    service.add(scope="project", scope_id="p1", kind="fact", content="项目使用北京仓库管理流程。")
    mixed = backend.keyword_search("北京 python", [("project", "p1")], 10)
    assert mixed and "北京" in mixed[0][0].content
    all_short = backend.keyword_search("查询 北京", [("project", "p1")], 10)
    assert all_short and "北京" in all_short[0][0].content


# --- 1. echo/grep must not be read as test/build verification --------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python -m pytest -q", True),
        ("npm test", True),
        ("npm run build", True),
        ("go build ./...", True),
        ("ruff check src", True),
        ("echo pytest", False),
        ("grep pytest README.md", False),
        ("echo 'tests passed' && pytest -q || true", False),
        ("go env", False),
        ("make install", False),
        ("ruff --version", False),
    ],
)
def test_is_verification_command(command: str, expected: bool):
    assert is_verification_command(command) is expected


def test_echo_after_a_failing_test_does_not_flip_the_outcome_to_success():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [
        Span(
            trace.trace_id,
            "tool",
            "bash",
            input={"command": "python -m unittest -q"},
            metadata={"returncode": 1},
            status="error",
        ),
        Span(trace.trace_id, "tool", "bash", input={"command": "echo pytest"}, metadata={"returncode": 0}, status="ok"),
    ]
    scores = {score.name: score.value for score in score_finished_trace(trace)}
    assert scores["verification"] == 0.0 and scores["outcome"] == 0.0


def test_an_unmatched_grep_does_not_count_as_a_failed_verification():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [
        Span(
            trace.trace_id,
            "tool",
            "bash",
            input={"command": "grep pytest README.md"},
            metadata={"returncode": 1},
            status="error",
        )
    ]
    scores = {score.name: score.value for score in score_finished_trace(trace)}
    assert "verification" not in scores and scores["outcome"] == 1.0


# --- 2. adopted rule/overlay content must match what the gate measured -----------------------


def test_overlay_whitespace_is_preserved_not_collapsed(tmp_path: Path):
    from vera_agent.memory.service import normalize_content

    overlay = "if ready:\n    run_tests()\n    report()"
    assert normalize_content(overlay, "rule") == overlay


# --- 3. two distinct proposals must not share, and fight over, one memory --------------------


def _state(tmp_path: Path):
    from types import SimpleNamespace

    return SimpleNamespace(projects_config_root=tmp_path, skill_mgr=None)


def test_adopting_an_identical_rule_twice_is_refused_not_silently_shared(tmp_path: Path):
    state = _state(tmp_path)
    store = ProposalStore.for_state(state)
    first = store.save(
        Proposal(kind="rule", title="a", content="先运行测试再回答。", rationale="r", status="recommended")
    )
    second = store.save(
        Proposal(kind="rule", title="b", content="先运行测试再回答。", rationale="r", status="recommended")
    )
    adopt(state, store, first.proposal_id)
    with pytest.raises(AdoptionError):
        adopt(state, store, second.proposal_id)
    # Rolling back the first proposal must not look like it also owns the second's intent.
    rollback(state, store, first.proposal_id, "test")
    assert active_profile(state, None, None).rules == []
    assert store.get(second.proposal_id).status == "recommended"


def test_rolling_back_one_proposal_never_deletes_a_different_proposals_rule(tmp_path: Path):
    state = _state(tmp_path)
    store = ProposalStore.for_state(state)
    a = adopt(
        state,
        store,
        store.save(
            Proposal(kind="rule", title="a", content="规则 A。", rationale="r", status="recommended")
        ).proposal_id,
    )
    b = adopt(
        state,
        store,
        store.save(
            Proposal(kind="rule", title="b", content="规则 B。", rationale="r", status="recommended")
        ).proposal_id,
    )
    rollback(state, store, a.proposal_id, "test")
    assert active_profile(state, None, None).rules == ["规则 B。"]
    assert memory_service_for_state(state).backend.get(b.adoption["memory_id"]).status == "active"


# --- 4. the online monitor must not mix traces from other projects ---------------------------


def _trace(store: TraceStore, project_id: str, outcome_ok: bool, start: float) -> None:
    trace = Trace(thread_id="t", project_id=project_id, exit_status="finish", start_time=start, end_time=start + 1)
    trace.spans = [
        Span(
            trace.trace_id,
            "tool",
            "bash",
            input={"command": "pytest"},
            metadata={"returncode": 0 if outcome_ok else 1},
            status="ok" if outcome_ok else "error",
        )
    ]
    score_finished_trace(trace)
    store.save_trace(trace)


def test_monitor_does_not_roll_back_a_project_proposal_on_another_projects_traces(tmp_path: Path):
    state = _state(tmp_path)
    store = ProposalStore.for_state(state)
    proposal = store.save(
        Proposal(
            kind="rule",
            title="t",
            content="项目规则。",
            rationale="r",
            scope="project",
            scope_id="p1",
            status="recommended",
        )
    )
    adopted = adopt(state, store, proposal.proposal_id)
    adopted_at = adopted.adoption["adopted_at"]
    traces = TraceStore.for_state(state)
    for index in range(10):
        _trace(traces, "p1", True, adopted_at - 3600 - index)  # p1 was healthy before adoption
    for index in range(10):
        _trace(traces, "p2", False, adopted_at + 1 + index)  # only an unrelated project regresses
    reports = check_adoptions(state, now=adopted_at + 60)
    assert reports[0]["action"] == "watching" and reports[0]["after_traces"] == 0
    assert store.get(proposal.proposal_id).status == "adopted"


# --- 5. a 1-2 character Chinese query must not silently return nothing -----------------------


def test_short_chinese_terms_fall_back_to_a_literal_match(tmp_path: Path):
    backend = SqliteMemoryBackend(tmp_path / "m.db")
    service = MemoryService(backend, backend)
    service.add(scope="project", scope_id="p1", kind="fact", content="项目使用北京仓库管理流程。")
    hits = backend.keyword_search("北京", [("project", "p1")], 10)
    assert hits and "北京" in hits[0][0].content

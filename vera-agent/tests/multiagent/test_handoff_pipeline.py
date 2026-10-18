"""Typed handoff chain, context watermark monitor, and automatic context rebirth pipeline."""

from pathlib import Path

from vera_agent.models.contracts import HandoverPayload
from vera_agent.session.pipeline import HandoffPipeline, WatermarkPolicy
from vera_agent.session.thread import ThreadSession
from vera_agent.tools.handoff_tools import (
    transfer_to_main_op,
    transfer_to_researcher_op,
    transfer_to_reviewer_op,
)


def test_watermark_policy_healthy():
    policy = WatermarkPolicy(max_turns=10, max_chars=5000, max_cost=0.50)
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    )
    breached, reason = policy.check(session)
    assert not breached
    assert "healthy" in reason.lower()


def test_watermark_policy_breached_by_turns():
    policy = WatermarkPolicy(max_turns=2, max_chars=50000, max_cost=10.0)
    session = ThreadSession(role="main")
    # Add 4 messages (2 user-assistant pairs = 2 turns)
    for i in range(4):
        session.add_messages({"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"})

    breached, reason = policy.check(session)
    assert breached
    assert "Turn limit exceeded" in reason


def test_watermark_policy_breached_by_chars():
    policy = WatermarkPolicy(max_turns=50, max_chars=100, max_cost=10.0)
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "a" * 60},
        {"role": "assistant", "content": "b" * 60},
    )
    breached, reason = policy.check(session)
    assert breached
    assert "character volume exceeded" in reason


def test_watermark_policy_breached_by_cost():
    policy = WatermarkPolicy(max_turns=50, max_chars=50000, max_cost=0.10)
    session = ThreadSession(role="main", cost=0.15)
    breached, reason = policy.check(session)
    assert breached
    assert "cost watermark exceeded" in reason


def test_handoff_pipeline_extract_payload():
    pipeline = HandoffPipeline()
    session = ThreadSession(role="researcher")
    session.add_messages(
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Investigate memory leak in cache module"},
        {"role": "assistant", "content": "- Circular reference in LRUCache\n- Missing __del__ cleanup"},
    )
    session.record_file_touch("cache/lru.py", "read")

    payload = pipeline.extract_handover_payload(
        session=session,
        target_role="main",
        rejected_paths=["Do not disable caching altogether"],
        next_action="Break circular ref with weakref",
    )

    assert isinstance(payload, HandoverPayload)
    assert payload.source_thread_id == session.thread_id
    assert "Investigate memory leak" in payload.target_problem
    assert "cache/lru.py" in payload.touched_files
    assert len(payload.key_findings) >= 1
    assert "Circular reference in LRUCache" in payload.key_findings[0]
    assert payload.rejected_paths == ["Do not disable caching altogether"]
    assert payload.next_action == "Break circular ref with weakref"


def test_handoff_pipeline_execute_handoff_with_archive(tmp_path: Path):
    archive_dir = tmp_path / "archives"
    pipeline = HandoffPipeline(archive_dir=archive_dir)

    session = ThreadSession(role="main", cost=0.04, n_calls=6)
    session.add_messages(
        {"role": "user", "content": "Refactor auth controller"},
        {"role": "assistant", "content": "Completed basic skeleton"},
    )
    session.record_file_touch("auth/controller.py", "write")

    new_session, payload = pipeline.execute_handoff(
        session=session,
        target_role="reviewer",
        target_problem="Review auth controller skeleton",
        extra_notes="Focus on SQL injection safety",
    )

    # 1. Verify archive created
    archived_file = archive_dir / f"{session.thread_id}_archived.json"
    assert archived_file.exists()

    # 2. Verify new session has pure inherited context
    assert new_session.role == "reviewer"
    assert new_session.parent_thread_id == session.thread_id
    assert new_session.metadata["parent_cost"] == 0.04
    assert len(new_session.messages) == 1

    content = new_session.messages[0]["content"]
    assert "SYSTEM HANDOVER ANCHOR" in content
    assert "auth/controller.py" in content
    assert "SQL injection safety" in content


def test_handoff_pipeline_auto_rebirth():
    policy = WatermarkPolicy(max_turns=2)
    pipeline = HandoffPipeline(policy=policy)

    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "Step 1"},
        {"role": "assistant", "content": "Done 1"},
    )

    # Within limits -> No rebirth
    did_rebirth, active_session, reason = pipeline.auto_rebirth_if_needed(session)
    assert not did_rebirth
    assert active_session.thread_id == session.thread_id

    # Breached -> Auto-rebirth
    session.add_messages(
        {"role": "user", "content": "Step 2"},
        {"role": "assistant", "content": "Done 2"},
    )
    did_rebirth2, active_session2, reason2 = pipeline.auto_rebirth_if_needed(session)
    assert did_rebirth2
    assert active_session2.thread_id != session.thread_id
    assert active_session2.parent_thread_id == session.thread_id
    assert "Turn limit exceeded" in reason2


def test_typed_handoff_tools():
    pipeline = HandoffPipeline()
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "Main task"},
        {"role": "assistant", "content": "Ready to delegate"},
    )

    # 1. transfer_to_researcher
    res_session, res_payload = transfer_to_researcher_op(
        session=session,
        pipeline=pipeline,
        task="Explore database migration options",
        scope=["models/", "migrations/"],
    )
    assert res_session.role == "researcher"
    assert "database migration" in res_payload.target_problem

    # 2. transfer_to_reviewer
    rev_session, rev_payload = transfer_to_reviewer_op(
        session=session,
        pipeline=pipeline,
        verification_focus="Audit security and test coverage",
    )
    assert rev_session.role == "reviewer"
    assert "Audit security" in rev_payload.target_problem

    # 3. transfer_to_main
    main_session, main_payload = transfer_to_main_op(
        session=res_session,
        pipeline=pipeline,
        summary="Exploration complete",
        key_findings=["Found 3 unapplied migrations"],
        rejected_paths=["Direct raw SQL execution"],
        recommended_next_action="Run alembic upgrade head",
    )
    assert main_session.role == "main"
    assert "Found 3 unapplied migrations" in main_payload.key_findings[0]
    assert main_payload.rejected_paths == ["Direct raw SQL execution"]

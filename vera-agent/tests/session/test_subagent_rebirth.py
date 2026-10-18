"""Subagent rebirth: triggers only after repeated ineffective compaction and keeps the full transcript."""

from types import SimpleNamespace

from vera_agent.session import context_management
from vera_agent.session.context_management import subagent_rebirth_if_needed
from vera_agent.session.thread import ThreadSession


def _fake_completion(**_kwargs):
    message = SimpleNamespace(content="CHECKPOINT: threshold 5 per 15 minutes, Redis key login_fail:<user>")
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)], usage={"prompt_tokens": 1, "completion_tokens": 1}
    )


def _crowded_session(checkpoints: int) -> ThreadSession:
    session = ThreadSession(role="researcher")
    session.add_messages({"role": "system", "content": "researcher"})
    session.add_messages({"role": "user", "content": "Investigate rate limiting."})
    for step in range(6):
        session.add_messages({"role": "assistant", "content": f"step {step}"})
        session.add_messages({"role": "user", "content": "log line " * 400})
    session.metadata["context_checkpoints"] = [{"summary": "old", "timestamp": 0}] * checkpoints
    return session


def test_rebirth_waits_for_repeated_compaction(monkeypatch):
    monkeypatch.setattr(context_management.litellm, "completion", _fake_completion)
    assert subagent_rebirth_if_needed(_crowded_session(2), "gpt-4o-mini", 4000) is None


def test_rebirth_rotates_context_and_reports_prior_compactions(monkeypatch):
    monkeypatch.setattr(context_management.litellm, "completion", _fake_completion)
    session = _crowded_session(3)
    messages_before = len(session.messages)

    event = subagent_rebirth_if_needed(session, "gpt-4o-mini", 4000)

    assert event is not None
    assert event["detail"].startswith("累计压缩 3 次")
    assert event["after_tokens"] < event["before_tokens"]
    assert len(session.messages) == messages_before
    assert session.metadata["context_events"][-1]["kind"] == "换血"

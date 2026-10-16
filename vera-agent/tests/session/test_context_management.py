from types import SimpleNamespace

from vera_agent.session import context_management
from vera_agent.session.thread import ThreadSession


def test_compaction_keeps_recent_turn_and_preserves_transcript(monkeypatch):
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": "Original task"},
        {
            "role": "assistant",
            "content": "Inspecting source",
            "tool_calls": [{"id": "call_read", "function": {"name": "read", "arguments": '{"path":"src.py"}'}}],
        },
        {"role": "tool", "tool_call_id": "call_read", "content": "Source excerpt"},
        {"role": "assistant", "content": "Earlier result"},
        {"role": "user", "content": "Latest question"},
        {"role": "assistant", "content": "Latest answer"},
    )
    original_messages = [dict(message) for message in session.messages]
    summary_prompts: list[str] = []

    monkeypatch.setattr(
        context_management.litellm,
        "token_counter",
        lambda *, model, messages: sum(len(str(message.get("content") or "")) for message in messages),
    )

    def fake_completion(*, model, messages, **kwargs):
        summary_prompts.append(messages[-1]["content"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Verified checkpoint"))],
            usage={"prompt_tokens": 12, "completion_tokens": 4},
        )

    monkeypatch.setattr(context_management.litellm, "completion", fake_completion)
    monkeypatch.setattr(context_management.litellm.cost_calculator, "completion_cost", lambda *args, **kwargs: 0)

    event = context_management.compact_session(
        session,
        "test-model",
        {},
        context_window=40,
        reserve_tokens=10,
        keep_recent_tokens=12,
    )

    assert event is not None
    assert event["kind"] == "压缩"
    assert event["before_tokens"] > 30
    assert session.messages == original_messages
    assert session.metadata["context_checkpoints"][-1]["summary"] == "Verified checkpoint"
    assert "answer-bearing source sentences close to verbatim" in summary_prompts[0]
    assert "Tool calls:" in summary_prompts[0]

    projected = context_management.context_projection(session)
    assert projected[0]["content"] == "System instructions"
    assert projected[1]["extra"]["compaction"] is True
    assert projected[1]["content"].endswith("Verified checkpoint")
    assert [message.get("content") for message in projected[-2:]] == ["Latest question", "Latest answer"]


def test_compaction_folds_an_oversized_older_turn_at_the_next_user_boundary(monkeypatch):
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "OVERSIZED_OLD_TURN " + ("older context " * 40)},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "Current question"},
    )
    summary_prompts: list[str] = []
    monkeypatch.setattr(
        context_management.litellm,
        "token_counter",
        lambda *, model, messages: sum(len(str(message.get("content") or "")) for message in messages),
    )

    def fake_completion(*, model, messages, **kwargs):
        summary_prompts.append(messages[-1]["content"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Checkpoint preserves OVERSIZED_OLD_TURN"))],
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )

    monkeypatch.setattr(context_management.litellm, "completion", fake_completion)
    monkeypatch.setattr(context_management.litellm.cost_calculator, "completion_cost", lambda *args, **kwargs: 0)

    event = context_management.compact_session(
        session,
        "test-model",
        {},
        context_window=80,
        reserve_tokens=10,
        keep_recent_tokens=50,
    )

    assert event is not None
    assert event["folded_message_count"] == 2
    assert event["kept_message_count"] == 1
    assert "OVERSIZED_OLD_TURN" in summary_prompts[0]
    assert [message.get("content") for message in context_management.context_projection(session)[-1:]] == ["Current question"]


def test_compaction_uses_minimum_summary_budget_and_retries_empty_response(monkeypatch):
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "user", "content": "Original material"},
        {"role": "assistant", "content": "Acknowledged"},
        {"role": "user", "content": "Question"},
    )
    monkeypatch.setattr(context_management, "_token_count", lambda messages, model: 100)
    monkeypatch.setattr(context_management.litellm, "get_model_info", lambda model: {"max_output_tokens": 8192})
    replies = ["", "Useful checkpoint"]
    requested_budgets = []

    def fake_completion(*, model, messages, **kwargs):
        requested_budgets.append(kwargs["max_tokens"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=replies.pop(0)))],
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )

    monkeypatch.setattr(context_management.litellm, "completion", fake_completion)
    monkeypatch.setattr(context_management.litellm.cost_calculator, "completion_cost", lambda *args, **kwargs: 0)

    event = context_management.compact_session(
        session,
        "test-model",
        {"max_tokens": 512},
        context_window=80,
        force=True,
        keep_recent_tokens=0,
    )

    assert event is not None
    assert requested_budgets == [2048, 2048]
    assert event["summary_attempts"] == 2
    assert event["summary_completion_tokens"] == 10
    assert event["token_count_basis"] == "local tokenizer estimate; not provider usage"
    assert session.n_calls == 2

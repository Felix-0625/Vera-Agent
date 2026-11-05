"""LitellmModel.query_stream: text streaming, tool-call assembly, usage, and retry rules after partial output."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vera_agent.exceptions import FormatError
from vera_agent.models.litellm_model import LitellmModel


def _chunk(*, text=None, tool=None, finish=None, usage=None, reasoning=None, model="gpt-4"):
    delta = SimpleNamespace(content=text, reasoning_content=reasoning, tool_calls=[tool] if tool else None)
    choices = [SimpleNamespace(index=0, delta=delta, finish_reason=finish)]
    return SimpleNamespace(id="s1", created=7, model=model, choices=choices, usage=usage)


def _tool(index, *, call_id=None, name=None, arguments=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=call_id, type="function" if call_id else None, function=function)


@pytest.fixture(autouse=True)
def _no_cost_lookup():
    with patch.object(LitellmModel, "_calculate_cost", MagicMock(return_value={"cost": 0.5})):
        yield


def _stream(chunks, **config):
    model = LitellmModel(model_name=config.pop("model_name", "gpt-4"), **config)
    seen: list[str] = []
    with patch.object(LitellmModel, "_query", return_value=chunks) as query:
        result = model.query_stream([{"role": "user", "content": "go"}], on_text=seen.append)
    return result, seen, query


def test_text_is_streamed_and_joined_with_usage_and_cost():
    usage = SimpleNamespace(model_dump=lambda: {"prompt_tokens": 3, "completion_tokens": 2})
    chunks = [_chunk(text="Hel"), _chunk(text="lo"), _chunk(finish="stop", usage=usage)]

    result, seen, query = _stream(chunks, allow_empty_tool_calls=True)

    assert seen == ["Hel", "lo"] and result["content"] == "Hello"
    assert result["extra"]["cost"] == 0.5 and result["extra"]["actions"] == []
    assert result["extra"]["response"]["usage"]["prompt_tokens"] == 3
    assert query.call_args.kwargs["stream"] is True
    assert query.call_args.kwargs["stream_options"] == {"include_usage": True}


def test_tool_call_fragments_are_assembled_by_index():
    chunks = [
        _chunk(tool=_tool(0, call_id="call_a", name="ba", arguments='{"comm')),
        _chunk(tool=_tool(0, name="sh", arguments='and": "ls"}')),
        _chunk(tool=_tool(1, call_id="call_b", name="bash", arguments='{"command": "pwd"}'), finish="tool_calls"),
    ]

    result, seen, _ = _stream(chunks)

    assert seen == []
    assert [call["id"] for call in result["tool_calls"]] == ["call_a", "call_b"]
    assert result["tool_calls"][0]["function"] == {"name": "bash", "arguments": '{"command": "ls"}'}
    assert result["extra"]["actions"] == [
        {"command": "ls", "tool_call_id": "call_a"},
        {"command": "pwd", "tool_call_id": "call_b"},
    ]


def test_a_reply_without_tool_calls_is_a_format_error_carrying_cost_and_response():
    with pytest.raises(FormatError) as caught:
        _stream([_chunk(text="just talking", finish="stop")])

    extra = caught.value.messages[0]["extra"]
    assert extra["cost"] == 0.5 and extra["response"]["choices"][0]["message"]["content"] == "just talking"


def test_non_deepseek_models_get_no_reasoning_field_unless_the_stream_has_reasoning():
    plain, _, _ = _stream([_chunk(text="x")], allow_empty_tool_calls=True)
    reasoned, _, _ = _stream([_chunk(text="x", reasoning="why")], allow_empty_tool_calls=True)

    assert "reasoning_content" not in plain
    assert reasoned["reasoning_content"] == "why"


def test_a_failure_before_any_output_is_retried():
    model = LitellmModel(model_name="gpt-4", allow_empty_tool_calls=True)
    good = [_chunk(text="ok", finish="stop")]
    with (
        patch.object(LitellmModel, "_query", side_effect=[RuntimeError("blip"), good]) as query,
        patch("tenacity.nap.time.sleep"),
    ):
        result = model.query_stream([{"role": "user", "content": "go"}], on_text=lambda _t: None)

    assert result["content"] == "ok" and query.call_count == 2


def test_a_failure_after_text_was_shown_is_raised_not_retried():
    def broken():
        yield _chunk(text="partial")
        raise ConnectionError("dropped mid-stream")

    model = LitellmModel(model_name="gpt-4", allow_empty_tool_calls=True)
    seen: list[str] = []
    with patch.object(LitellmModel, "_query", return_value=broken()) as query:
        with pytest.raises(ConnectionError, match="dropped mid-stream"):
            model.query_stream([{"role": "user", "content": "go"}], on_text=seen.append)

    assert seen == ["partial"] and query.call_count == 1

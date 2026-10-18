from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vera_agent.exceptions import FormatError
from vera_agent.models.litellm_model import LitellmModel, LitellmModelConfig
from vera_agent.models.utils.actions_toolcall import ALL_TOOLS


class TestLitellmModelConfig:
    def test_default_format_error_template(self):
        assert LitellmModelConfig(model_name="test").format_error_template == "{{ error }}"


def _mock_litellm_response(tool_calls):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = tool_calls
    mock_response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": None}
    mock_response.model_dump.return_value = {}
    return mock_response


class TestLitellmModel:
    def test_deepseek_request_preparation_preserves_and_fills_reasoning_content(self):
        model = LitellmModel(model_name="deepseek/deepseek-flash")
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1"}]},
            {"role": "assistant", "content": "done", "reasoning_content": "preserve me"},
            {"role": "tool", "content": "result"},
        ]

        prepared = model._prepare_messages_for_api(messages)

        assert prepared[0]["reasoning_content"] == ""
        assert prepared[1]["reasoning_content"] == "preserve me"
        assert "reasoning_content" not in prepared[2]

    @patch("vera_agent.models.litellm_model.LitellmModel._calculate_cost", new=MagicMock(return_value={"cost": 0.0}))
    @patch("vera_agent.models.litellm_model.LitellmModel._query")
    def test_query_stream_preserves_reasoning_content(self, mock_query):
        delta = SimpleNamespace(content=None, reasoning_content="tool reasoning")
        choice = SimpleNamespace(index=0, delta=delta, finish_reason="stop")
        chunk = SimpleNamespace(
            id="stream-1",
            created=1,
            model="deepseek/deepseek-flash",
            choices=[choice],
            usage=None,
        )
        mock_query.return_value = [chunk]

        model = LitellmModel(model_name="deepseek/deepseek-flash", allow_empty_tool_calls=True)
        result = model.query_stream([{"role": "user", "content": "test"}], on_text=lambda _text: None)

        assert result["reasoning_content"] == "tool reasoning"

    @patch("vera_agent.models.litellm_model.LitellmModel._calculate_cost", new=MagicMock(return_value={"cost": 0.0}))
    @patch("vera_agent.models.litellm_model.LitellmModel._query")
    def test_query_stream_preserves_final_message_reasoning_content(self, mock_query):
        choice = SimpleNamespace(
            index=0,
            delta=None,
            message=SimpleNamespace(reasoning_content="final reasoning"),
            finish_reason="stop",
        )
        mock_query.return_value = [
            SimpleNamespace(
                id="stream-2",
                created=1,
                model="deepseek/deepseek-flash",
                choices=[choice],
                usage=None,
            )
        ]

        model = LitellmModel(model_name="deepseek/deepseek-flash", allow_empty_tool_calls=True)
        result = model.query_stream([{"role": "user", "content": "test"}], on_text=lambda _text: None)

        assert result["reasoning_content"] == "final reasoning"

    @patch("vera_agent.models.litellm_model.LitellmModel._calculate_cost", new=MagicMock(return_value={"cost": 0.0}))
    @patch("vera_agent.models.litellm_model.LitellmModel._query")
    def test_query_stream_keeps_empty_deepseek_reasoning_field(self, mock_query):
        choice = SimpleNamespace(index=0, delta=SimpleNamespace(content=None), message=None, finish_reason="stop")
        mock_query.return_value = [
            SimpleNamespace(
                id="stream-3",
                created=1,
                model="deepseek/deepseek-flash",
                choices=[choice],
                usage=None,
            )
        ]

        model = LitellmModel(model_name="deepseek/deepseek-flash", allow_empty_tool_calls=True)
        result = model.query_stream([{"role": "user", "content": "test"}], on_text=lambda _text: None)

        assert "reasoning_content" in result
        assert result["reasoning_content"] == ""

    @patch("vera_agent.models.litellm_model.litellm.completion")
    @patch("vera_agent.models.litellm_model.litellm.cost_calculator.completion_cost")
    def test_query_includes_all_tools(self, mock_cost, mock_completion):
        tool_call = MagicMock()
        tool_call.function.name = "bash"
        tool_call.function.arguments = '{"command": "echo test"}'
        tool_call.id = "call_1"
        mock_completion.return_value = _mock_litellm_response([tool_call])
        mock_cost.return_value = 0.001

        model = LitellmModel(model_name="gpt-4")
        model.query([{"role": "user", "content": "test"}])

        mock_completion.assert_called_once()
        assert mock_completion.call_args.kwargs["tools"] == ALL_TOOLS

    @patch("vera_agent.models.litellm_model.litellm.completion")
    @patch("vera_agent.models.litellm_model.litellm.cost_calculator.completion_cost")
    def test_parse_actions_valid_tool_call(self, mock_cost, mock_completion):
        tool_call = MagicMock()
        tool_call.function.name = "bash"
        tool_call.function.arguments = '{"command": "ls -la"}'
        tool_call.id = "call_abc"
        mock_completion.return_value = _mock_litellm_response([tool_call])
        mock_cost.return_value = 0.001

        model = LitellmModel(model_name="gpt-4")
        result = model.query([{"role": "user", "content": "list files"}])
        assert result["extra"]["actions"] == [{"command": "ls -la", "tool_call_id": "call_abc"}]

    @patch("vera_agent.models.litellm_model.litellm.completion")
    @patch("vera_agent.models.litellm_model.litellm.cost_calculator.completion_cost")
    def test_parse_actions_no_tool_calls_raises(self, mock_cost, mock_completion):
        mock_completion.return_value = _mock_litellm_response(None)
        mock_cost.return_value = 0.001

        model = LitellmModel(model_name="gpt-4")
        with pytest.raises(FormatError):
            model.query([{"role": "user", "content": "test"}])

    @patch("vera_agent.models.litellm_model.litellm.completion")
    @patch("vera_agent.models.litellm_model.litellm.cost_calculator.completion_cost")
    def test_finish_reason_threaded_into_format_error_template(self, mock_cost, mock_completion):
        """The response finish_reason is exposed to format_error_template via template_kwargs, so a
        config can report a max_tokens truncation instead of the misleading "no tool call" error."""
        response = _mock_litellm_response(None)
        response.choices[0].finish_reason = "length"
        mock_completion.return_value = response
        mock_cost.return_value = 0.001

        model = LitellmModel(
            model_name="gpt-4",
            format_error_template="{% if finish_reason == 'length' %}cut off{% else %}{{ error }}{% endif %}",
        )
        with pytest.raises(FormatError) as exc:
            model.query([{"role": "user", "content": "test"}])
        assert exc.value.messages[0]["content"] == "cut off"

    def test_format_observation_messages(self):
        model = LitellmModel(model_name="gpt-4", observation_template="{{ output.output }}")
        message = {"extra": {"actions": [{"command": "echo test", "tool_call_id": "call_1"}]}}
        outputs = [{"output": "test output", "returncode": 0}]
        result = model.format_observation_messages(message, outputs)
        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_1"
        assert result[0]["content"] == "test output"

    def test_format_observation_messages_no_actions(self):
        model = LitellmModel(model_name="gpt-4")
        result = model.format_observation_messages({"extra": {}}, [])
        assert result == []

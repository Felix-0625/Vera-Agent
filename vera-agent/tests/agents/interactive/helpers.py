"""Shared deterministic model helpers."""

from contextlib import contextmanager
from unittest.mock import patch

from vera_agent.agents.interactive import InteractiveAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.test_models import (
    DeterministicModel,
    DeterministicResponseAPIToolcallModel,
    DeterministicToolcallModel,
    make_output,
    make_response_api_output,
    make_toolcall_output,
)


@contextmanager
def mock_prompts(side_effect):
    """Patch both single-line and multiline prompt sessions with shared side_effect."""
    if callable(side_effect):
        se = side_effect
    else:
        it = iter(side_effect)

        def se(*args, **kwargs):
            return next(it)

    with patch("vera_agent.agents.utils.prompt_user.prompt_session.prompt", side_effect=se):
        with patch("vera_agent.agents.utils.prompt_user._multiline_prompt_session.prompt", side_effect=se):
            yield


def get_text(msg: dict) -> str:
    """Extract text content from a message regardless of format."""
    content = msg.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content:
        return content[0].get("text", "")
    return ""


def make_text_model(outputs_spec: list[tuple[str, list[dict]]], **kwargs) -> DeterministicModel:
    """Create a DeterministicModel from a list of (content, actions) tuples."""
    return DeterministicModel(outputs=[make_output(content, actions) for content, actions in outputs_spec], **kwargs)


def make_tc_model(outputs_spec: list[tuple[str, list[dict]]], **kwargs) -> DeterministicToolcallModel:
    """Create a DeterministicToolcallModel from a list of (content, actions) tuples."""
    outputs = []
    for i, (content, actions) in enumerate(outputs_spec):
        tc_actions = []
        tool_calls = []
        for j, action in enumerate(actions):
            tool_call_id = f"call_{i}_{j}"
            tc_actions.append({"command": action["command"], "tool_call_id": tool_call_id})
            tool_calls.append(
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": "bash", "arguments": f'{{"command": "{action["command"]}"}}'},
                }
            )
        outputs.append(make_toolcall_output(content, tool_calls, tc_actions))
    return DeterministicToolcallModel(outputs=outputs, **kwargs)


def make_response_api_model(
    outputs_spec: list[tuple[str, list[dict]]], **kwargs
) -> DeterministicResponseAPIToolcallModel:
    """Create a DeterministicResponseAPIToolcallModel from a list of (content, actions) tuples."""
    outputs = []
    for i, (content, actions) in enumerate(outputs_spec):
        api_actions = []
        for j, action in enumerate(actions):
            tool_call_id = f"call_resp_{i}_{j}"
            api_actions.append({"command": action["command"], "tool_call_id": tool_call_id})
        outputs.append(make_response_api_output(content, api_actions))
    return DeterministicResponseAPIToolcallModel(outputs=outputs, **kwargs)


def _make_model(outputs: list[tuple[str, list[dict]]], **kwargs) -> DeterministicModel:
    """Create a DeterministicModel from a list of (content, actions) tuples.

    Kept for backward compatibility with tests that don't need parametrization.
    """
    return make_text_model(outputs, **kwargs)


def _test_interruption_helper(
    factory, config, interruption_input, expected_message_fragment, problem_statement="Test interruption"
):
    """Helper function for testing interruption scenarios."""
    agent = InteractiveAgent(
        model=factory(
            [
                ("Initial step", [{"command": "echo 'will be interrupted'"}]),
                (
                    "Recovery",
                    [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'recovered from interrupt'"}],
                ),
            ]
        ),
        env=LocalEnvironment(),
        **config,
    )

    # Mock the query to raise KeyboardInterrupt on first call, then work normally
    original_query = agent.query
    call_count = 0

    def mock_query(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise KeyboardInterrupt()
        return original_query(*args, **kwargs)

    # Mock console.input based on the interruption_input parameter
    input_call_count = 0

    def mock_input(prompt, **kwargs):
        nonlocal input_call_count
        input_call_count += 1
        if input_call_count == 1:
            return interruption_input  # For the interruption handling
        return ""  # Confirm all subsequent actions

    with mock_prompts(mock_input):
        with patch.object(agent, "query", side_effect=mock_query):
            info = agent.run(problem_statement)

    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "recovered from interrupt\n"
    # Check that the expected interruption message was added
    interrupt_messages = [msg for msg in agent.messages if expected_message_fragment in get_text(msg)]
    assert len(interrupt_messages) == 1

    return agent, interrupt_messages[0]

"""Permissions regression coverage."""

from unittest.mock import patch

from vera_agent.agents.interactive import InteractiveAgent
from vera_agent.environments.local import LocalEnvironment

from .helpers import mock_prompts


def test_complex_mode_switching_sequence(model_factory):
    """Test complex sequence of mode switches across different contexts."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory(
            [
                ("Action 1", [{"command": "echo 'action1'"}]),
                ("Action 2", [{"command": "echo 'action2'"}]),
                ("Action 3", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'final action'"}]),
            ]
        ),
        env=LocalEnvironment(),
        **{
            **config,
            "mode": "confirm",
        },
    )

    # Mock interruption on second query
    original_query = agent.query
    call_count = 0

    def mock_query(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise KeyboardInterrupt()
        return original_query(*args, **kwargs)

    with mock_prompts(
        [
            "/y",  # Confirm->Yolo during first action confirmation
            "/u",  # Yolo->Human during interrupt
            "/c",  # Human->Confirm in human mode
            "",  # Confirm final action
            "",  # No new task when agent wants to finish
            "",  # Extra empty input for any additional prompts
            "",  # Extra empty input for any additional prompts
        ]
    ):
        with patch.object(agent, "query", side_effect=mock_query):
            info = agent.run("Test complex mode switching")

    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "final action\n"
    assert agent.config.mode == "confirm"  # Should end in confirm mode

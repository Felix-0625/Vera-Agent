"""Limits regression coverage."""

from unittest.mock import patch

from vera_agent.agents.interactive import InteractiveAgent
from vera_agent.environments.local import LocalEnvironment

from .helpers import mock_prompts


def test_limits_exceeded_with_user_continuation(model_factory):
    """Test that when limits are exceeded, user can provide new limits and execution continues."""
    factory, config = model_factory
    # Create agent with very low limits that will be exceeded
    agent = InteractiveAgent(
        model=factory(
            [
                ("Step 1", [{"command": "echo 'first step'"}]),
                ("Step 2", [{"command": "echo 'second step'"}]),
                (
                    "Final step",
                    [
                        {
                            "command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed after limit increase'"
                        }
                    ],
                ),
            ],
            cost_per_call=0.6,  # Will exceed cost_limit=0.5 on first call
        ),
        env=LocalEnvironment(),
        **{
            **config,
            "step_limit": 10,  # High enough to not interfere initially
            "cost_limit": 0.5,  # Will be exceeded with first model call (cost=0.6),
            "mode": "yolo",  # Use yolo mode to avoid confirmation prompts,
        },
    )

    # Mock input() to provide new limits when prompted (simulating an
    # interactive terminal, so isatty() must report True).
    with patch.object(InteractiveAgent, "_stdin_is_interactive", return_value=True):
        with patch("builtins.input", side_effect=["10", "5.0"]):  # New step_limit=10, cost_limit=5.0
            with mock_prompts([""]):  # No new task
                with patch("vera_agent.agents.interactive.console.print"):  # Suppress console output
                    info = agent.run("Test limits exceeded with continuation")

    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "completed after limit increase\n"
    assert agent.n_calls == 3  # Should complete all 3 steps
    assert agent.config.step_limit == 10  # Should have updated step limit
    assert agent.config.cost_limit == 5.0  # Should have updated cost limit


def test_limits_exceeded_multiple_times_with_continuation(model_factory):
    """Test that limits can be exceeded and updated multiple times."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory(
            [
                ("Step 1", [{"command": "echo 'step1'"}]),
                ("Step 2", [{"command": "echo 'step2'"}]),
                ("Step 3", [{"command": "echo 'step3'"}]),
                ("Step 4", [{"command": "echo 'step4'"}]),
                (
                    "Final",
                    [
                        {
                            "command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed after multiple increases'"
                        }
                    ],
                ),
            ],
            cost_per_call=1.0,  # Standard cost per call
        ),
        env=LocalEnvironment(),
        **{
            **config,
            "step_limit": 1,  # Will be exceeded after first step
            "cost_limit": 100.0,  # High enough to not interfere,
            "mode": "yolo",
        },
    )

    # Mock input() to provide new limits multiple times (interactive terminal).
    # First limit increase: step_limit=2, then step_limit=10 when exceeded again
    with patch.object(InteractiveAgent, "_stdin_is_interactive", return_value=True):
        with patch("builtins.input", side_effect=["2", "100.0", "10", "100.0"]):
            with mock_prompts([""]):  # No new task
                with patch("vera_agent.agents.interactive.console.print"):
                    info = agent.run("Test multiple limit increases")

    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "completed after multiple increases\n"
    assert agent.n_calls == 5  # Should complete all 5 steps
    assert agent.config.step_limit == 10  # Should have final updated step limit


def test_limits_exceeded_non_interactive_stops_cleanly(model_factory):
    """Without a terminal (e.g. `--yolo` in CI / a sandbox), a breached limit must
    stop cleanly with a LimitsExceeded exit status instead of crashing on EOFError
    when trying to prompt for new limits."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory(
            [("Step 1", [{"command": "echo 'first step'"}])],
            cost_per_call=0.6,  # exceeds cost_limit after the first call
        ),
        env=LocalEnvironment(),
        **{
            **config,
            "step_limit": 10,
            "cost_limit": 0.5,
            "mode": "yolo",
        },
    )

    with patch.object(InteractiveAgent, "_stdin_is_interactive", return_value=False):
        with patch("builtins.input", side_effect=AssertionError("input() must not be called")) as mock_in:
            with patch("vera_agent.agents.interactive.console.print"):
                info = agent.run("Test non-interactive limit stop")

    assert info["exit_status"] == "LimitsExceeded"
    assert agent.n_calls == 1  # one model call happened, the next was blocked by the limit
    mock_in.assert_not_called()


def test_time_exceeded_never_prompts(model_factory):
    """A wall-clock limit can't be lifted by raising step/cost limits, so it must
    always stop cleanly -- even with an interactive terminal -- rather than prompt
    (which would otherwise loop forever)."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory([("Step 1", [{"command": "echo 'first step'"}])]),
        env=LocalEnvironment(),
        **{**config, "step_limit": 10, "cost_limit": 100.0, "wall_time_limit_seconds": 1, "mode": "yolo"},
    )
    agent._start_time = 0  # force the wall-clock budget to be already exhausted

    with patch.object(InteractiveAgent, "_stdin_is_interactive", return_value=True):
        with patch("builtins.input", side_effect=AssertionError("input() must not be called")) as mock_in:
            with patch("vera_agent.agents.interactive.console.print"):
                info = agent.run("Test time-exceeded clean stop")

    assert info["exit_status"] == "TimeExceeded"
    assert agent.n_calls == 0  # limit tripped before any model call
    mock_in.assert_not_called()

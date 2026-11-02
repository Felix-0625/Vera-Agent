"""Completion regression coverage."""

from unittest.mock import patch

from vera_agent.agents.interactive import InteractiveAgent
from vera_agent.environments.local import LocalEnvironment

from .helpers import get_text, mock_prompts


def test_continue_after_completion_with_new_task(model_factory):
    """Test that user can provide a new task when agent wants to finish."""
    factory, config = model_factory
    with mock_prompts(
        [
            "",  # Confirm first action
            "Create a new file",  # Provide new task when agent wants to finish
            "",  # Confirm second action for new task
            "",  # Don't provide another task after second completion (finish)
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "First task",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'first task completed'"}],
                    ),
                    (
                        "Second task",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'new task completed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Complete the initial task")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "new task completed\n"
        assert agent.n_calls == 2
        # Should have the new task message in conversation
        new_task_messages = [
            msg for msg in agent.messages if "The user added a new task: Create a new file" in get_text(msg)
        ]
        assert len(new_task_messages) == 1


def test_continue_after_completion_without_new_task(model_factory):
    """Test that agent finishes normally when user doesn't provide a new task."""
    factory, config = model_factory
    with mock_prompts(
        [
            "",  # Confirm first action
            "",  # Don't provide new task when agent wants to finish (empty input)
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "Task completion",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'original task completed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Complete the task")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "original task completed\n"
        assert agent.n_calls == 1
        # Should not have any new task messages
        new_task_messages = [msg for msg in agent.messages if "The user added a new task" in get_text(msg)]
        assert len(new_task_messages) == 0


def test_continue_after_completion_multiple_cycles(model_factory):
    """Test multiple continuation cycles with new tasks."""
    factory, config = model_factory
    with mock_prompts(
        [
            "",  # Confirm first action
            "Second task",  # Provide first new task
            "",  # Confirm second action
            "Third task",  # Provide second new task
            "",  # Confirm third action
            "",  # Don't provide another task (finish)
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'first completed'"}]),
                    ("Second", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'second completed'"}]),
                    ("Third", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'third completed'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Initial task")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "third completed\n"
        assert agent.n_calls == 3
        # Should have both new task messages
        new_task_messages = [msg for msg in agent.messages if "The user added a new task" in get_text(msg)]
        assert len(new_task_messages) == 2
        assert "Second task" in get_text(new_task_messages[0])
        assert "Third task" in get_text(new_task_messages[1])


def test_continue_after_completion_in_yolo_mode(model_factory):
    """Test continuation when starting in yolo mode (no confirmations needed)."""
    factory, config = model_factory
    with mock_prompts(
        [
            "Create a second task",  # Provide new task when agent wants to finish
            "",  # Don't provide another task after second completion (finish)
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'first completed'"}]),
                    (
                        "Second",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'second task completed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "yolo",  # Start in yolo mode
            },
        )

        info = agent.run("Initial task")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "second task completed\n"
        assert agent.config.mode == "yolo"
        assert agent.n_calls == 2
        # Should have the new task message
        new_task_messages = [msg for msg in agent.messages if "Create a second task" in get_text(msg)]
        assert len(new_task_messages) == 1


def test_confirm_exit_enabled_asks_for_confirmation(model_factory):
    """Test that when confirm_exit=True, agent asks for confirmation before finishing."""
    factory, config = model_factory
    with mock_prompts(["", ""]):  # Confirm action, then no new task (empty string to exit)
        agent = InteractiveAgent(
            model=factory(
                [
                    ("Finishing", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "confirm_exit": True,  # Should ask for confirmation
            },
        )

        info = agent.run("Test confirm exit enabled")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "completed\n"
        assert agent.n_calls == 1


def test_confirm_exit_disabled_exits_immediately(model_factory):
    """Test that when confirm_exit=False, agent exits immediately without asking."""
    factory, config = model_factory
    with mock_prompts([""]):  # Only confirm action, no exit confirmation needed
        agent = InteractiveAgent(
            model=factory(
                [
                    ("Finishing", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "confirm_exit": False,  # Should NOT ask for confirmation
            },
        )

        info = agent.run("Test confirm exit disabled")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "completed\n"
        assert agent.n_calls == 1


def test_confirm_exit_with_new_task_continues_execution(model_factory):
    """Test that when user provides new task at exit confirmation, agent continues."""
    factory, config = model_factory
    with mock_prompts(
        [
            "",  # Confirm first action
            "Please do one more thing",  # Provide new task instead of exiting
            "",  # Confirm second action
            "",  # No new task on second exit confirmation
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First task", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'first done'"}]),
                    (
                        "Additional task",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'additional done'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "confirm_exit": True,
            },
        )

        info = agent.run("Test exit with new task")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "additional done\n"
        assert agent.n_calls == 2
        # Check that the new task was added to the conversation
        new_task_messages = [msg for msg in agent.messages if "Please do one more thing" in get_text(msg)]
        assert len(new_task_messages) == 1


def test_confirm_exit_config_field_defaults(model_factory):
    """Test that confirm_exit field has correct default value."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory([]),
        env=LocalEnvironment(),
        **config,
    )
    # Default should be True
    assert agent.config.confirm_exit is True


def test_confirm_exit_config_field_can_be_set(model_factory):
    """Test that confirm_exit field can be explicitly set."""
    factory, config = model_factory
    agent_with_confirm = InteractiveAgent(
        model=factory([]),
        env=LocalEnvironment(),
        **{
            **config,
            "confirm_exit": True,
        },
    )
    assert agent_with_confirm.config.confirm_exit is True

    agent_without_confirm = InteractiveAgent(
        model=factory([]),
        env=LocalEnvironment(),
        **{
            **config,
            "confirm_exit": False,
        },
    )
    assert agent_without_confirm.config.confirm_exit is False


def test_submission_help_then_human_mode(model_factory):
    """Test: agent submits → /h shows help and reprompts → /u switches to human → echo 'test' → see 'test'."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/h",  # At submission prompt: show help, reprompt
            "/u",  # At submission prompt: switch to human mode
            "echo 'test'",  # In human mode: run command
            "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'done'",  # Submit from human mode
            "",  # Confirm exit
        ]
    ):
        with patch("vera_agent.agents.interactive.console.print") as mock_print:
            agent = InteractiveAgent(
                model=factory(
                    [("Finishing", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'initial'"}])],
                ),
                env=LocalEnvironment(),
                **{**config, "mode": "yolo"},
            )
            info = agent.run("Solve the issue")
    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "done\n"
    assert agent.config.mode == "human"
    assert agent.n_calls == 1
    # Help was shown
    assert any("/y" in str(c) for c in mock_print.call_args_list)
    # echo 'test' output is visible in the conversation
    assert any("test" in get_text(msg) for msg in agent.messages)


def test_submission_enter_quits(model_factory):
    """Test: agent submits → Enter → quit for real."""
    factory, config = model_factory
    with mock_prompts([""]):  # At submission prompt: Enter to quit
        agent = InteractiveAgent(
            model=factory(
                [("Finishing", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed'"}])],
            ),
            env=LocalEnvironment(),
            **{**config, "mode": "yolo"},
        )
        info = agent.run("Solve the issue")
    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "completed\n"
    assert agent.n_calls == 1

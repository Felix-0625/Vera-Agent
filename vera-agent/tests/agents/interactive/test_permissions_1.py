"""Permissions regression coverage."""

from unittest.mock import patch

from vera_agent.agents.interactive import InteractiveAgent
from vera_agent.environments.local import LocalEnvironment

from .helpers import _test_interruption_helper, get_text, mock_prompts


def test_successful_completion_with_confirmation(model_factory):
    """Test agent completes successfully when user confirms all actions."""
    factory, config = model_factory
    with mock_prompts(["", ""]):  # Confirm action with Enter, then no new task
        agent = InteractiveAgent(
            model=factory(
                [
                    ("Finishing", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'completed'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Test completion with confirmation")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "completed\n"
        assert agent.n_calls == 1


def test_action_rejection_and_recovery(model_factory):
    """Test agent handles action rejection and can recover."""
    factory, config = model_factory
    with mock_prompts(
        [
            "User rejected this action",  # Reject first action
            "",  # Confirm second action
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First try", [{"command": "echo 'first attempt'"}]),
                    ("Second try", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'recovered'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Test action rejection")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "recovered\n"
        assert agent.n_calls == 2
        # Should have rejection message in conversation
        rejection_messages = [msg for msg in agent.messages if "User rejected this action" in get_text(msg)]
        assert len(rejection_messages) == 1


def test_yolo_mode_activation(model_factory):
    """Test entering yolo mode disables confirmations."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/y",  # Enter yolo mode
            "",  # This should be ignored since yolo mode is on
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("Test command", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'yolo works'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Test yolo mode")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "yolo works\n"
        assert agent.config.mode == "yolo"


def test_help_command(model_factory):
    """Test help command shows help and continues normally."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/h",  # Show help
            "",  # Confirm action after help
            "",  # No new task when agent wants to finish
        ]
    ):
        with patch("vera_agent.agents.interactive.console.print") as mock_print:
            agent = InteractiveAgent(
                model=factory(
                    [
                        ("Test help", [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'help shown'"}]),
                    ]
                ),
                env=LocalEnvironment(),
                **config,
            )

            info = agent.run("Test help command")
            assert info["exit_status"] == "Submitted"
            assert info["submission"] == "help shown\n"
            # Check that help was printed
            help_calls = [call for call in mock_print.call_args_list if "/y" in str(call)]
            assert len(help_calls) > 0


def test_whitelisted_actions_skip_confirmation(model_factory):
    """Test that whitelisted actions don't require confirmation."""
    factory, config = model_factory
    with mock_prompts([""]):  # No new task when agent wants to finish
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "Whitelisted",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'no confirmation needed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "whitelist_actions": [r"echo.*"],
            },
        )

        info = agent.run("Test whitelisted actions")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "no confirmation needed\n"


def test_interruption_handling_with_message(model_factory):
    """Test that interruption with user message is handled properly."""
    factory, config = model_factory
    agent, interrupt_message = _test_interruption_helper(factory, config, "User interrupted", "Interrupted by user")

    # Additional verification specific to this test
    assert "User interrupted" in get_text(interrupt_message)


def test_interruption_handling_empty_message(model_factory):
    """Test that interruption with empty input is handled properly."""
    factory, config = model_factory
    _test_interruption_helper(factory, config, "", "Temporary interruption caught")


def test_multiple_confirmations_and_commands(model_factory):
    """Test complex interaction with multiple confirmations and commands."""
    factory, config = model_factory
    with mock_prompts(
        [
            "reject first",  # Reject first action
            "/h",  # Show help for second action
            "/y",  # After help, enter yolo mode
            "",  # After yolo mode enabled, confirm (but yolo mode will skip future confirmations)
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First action", [{"command": "echo 'first'"}]),
                    (
                        "Second action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'complex flow completed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **config,
        )

        info = agent.run("Test complex interaction flow")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "complex flow completed\n"
        assert agent.config.mode == "yolo"  # Should be in yolo mode
        assert agent.n_calls == 2


def test_non_whitelisted_action_requires_confirmation(model_factory):
    """Test that non-whitelisted actions still require confirmation."""
    factory, config = model_factory
    with mock_prompts(["", ""]):  # Confirm action, then no new task
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "Non-whitelisted",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'confirmed'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "whitelist_actions": [r"ls.*"],  # Only ls commands whitelisted
            },
        )

        info = agent.run("Test non-whitelisted action")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "confirmed\n"


def test_human_mode_basic_functionality(model_factory):
    """Test human mode where user enters shell commands directly."""
    factory, config = model_factory
    with mock_prompts(
        [
            "echo 'user command'",  # User enters shell command
            "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'human mode works'",  # User enters final command
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory([]),  # LM shouldn't be called in human mode
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "human",
            },
        )

        info = agent.run("Test human mode")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "human mode works\n"
        assert agent.config.mode == "human"
        assert agent.n_calls == 0  # LM should not be called


def test_human_mode_switch_to_yolo(model_factory):
    """Test switching from human mode to yolo mode."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/y",  # Switch to yolo mode from human mode
            "",  # Confirm action in yolo mode (though no confirmation needed)
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "LM action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'switched to yolo'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "human",
            },
        )

        info = agent.run("Test human to yolo switch")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "switched to yolo\n"
        assert agent.config.mode == "yolo"
        assert agent.n_calls == 1


def test_human_mode_switch_to_confirm(model_factory):
    """Test switching from human mode to confirm mode."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/c",  # Switch to confirm mode from human mode
            "",  # Confirm action in confirm mode
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "LM action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'switched to confirm'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "human",
            },
        )

        info = agent.run("Test human to confirm switch")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "switched to confirm\n"
        assert agent.config.mode == "confirm"
        assert agent.n_calls == 1


def test_confirmation_mode_switch_to_human_with_rejection(model_factory):
    """Test switching from confirm mode to human mode with /u command."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/u",  # Switch to human mode and reject action
            "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'human command after rejection'",  # Human command
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("LM action", [{"command": "echo 'first action'"}]),
                    ("Recovery action", [{"command": "echo 'recovery'"}]),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "confirm",
            },
        )

        info = agent.run("Test confirm to human switch")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "human command after rejection\n"
        assert agent.config.mode == "human"
        # Should have rejection message
        rejection_messages = [msg for msg in agent.messages if "Switching to human mode" in get_text(msg)]
        assert len(rejection_messages) == 1


def test_confirmation_mode_switch_to_yolo_and_continue(model_factory):
    """Test switching from confirm mode to yolo mode with /y and continuing with action."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/y",  # Switch to yolo mode and confirm current action
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "LM action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'switched and continued'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "confirm",
            },
        )

        info = agent.run("Test confirm to yolo switch")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "switched and continued\n"
        assert agent.config.mode == "yolo"


def test_mode_switch_during_keyboard_interrupt(model_factory):
    """Test mode switching during keyboard interrupt handling."""
    factory, config = model_factory
    agent = InteractiveAgent(
        model=factory(
            [
                ("Initial step", [{"command": "echo 'will be interrupted'"}]),
                (
                    "Recovery",
                    [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'recovered after mode switch'"}],
                ),
            ]
        ),
        env=LocalEnvironment(),
        **{
            **config,
            "mode": "confirm",
        },
    )

    # Mock the query to raise KeyboardInterrupt on first call
    original_query = agent.query
    call_count = 0

    def mock_query(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise KeyboardInterrupt()
        return original_query(*args, **kwargs)

    with mock_prompts(
        [
            "/y",  # Switch to yolo mode during interrupt
            "",  # Confirm subsequent actions (though yolo mode won't ask)
        ]
    ):
        with patch.object(agent, "query", side_effect=mock_query):
            info = agent.run("Test interrupt mode switch")

    assert info["exit_status"] == "Submitted"
    assert info["submission"] == "recovered after mode switch\n"
    assert agent.config.mode == "yolo"
    # Should have interruption message
    interrupt_messages = [msg for msg in agent.messages if "Temporary interruption caught" in get_text(msg)]
    assert len(interrupt_messages) == 1


def test_already_in_mode_behavior(model_factory):
    """Test behavior when trying to switch to the same mode."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/c",  # Try to switch to confirm mode when already in confirm mode
            "",  # Confirm action after the "already in mode" recursive prompt
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    (
                        "Test action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'already in mode'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "confirm",
            },
        )

        info = agent.run("Test already in mode")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "already in mode\n"
        assert agent.config.mode == "confirm"


def test_all_mode_transitions_yolo_to_others(model_factory):
    """Test transitions from yolo mode to other modes."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/c",  # Switch from yolo to confirm
            "",  # Confirm action in confirm mode
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory(
                [
                    ("First action", [{"command": "echo 'yolo action'"}]),
                    (
                        "Second action",
                        [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'confirm action'"}],
                    ),
                ]
            ),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "yolo",
            },
        )

        # Trigger first action in yolo mode (should execute without confirmation)
        # Then interrupt to switch mode
        original_query = agent.query
        call_count = 0

        def mock_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Interrupt on second query
                raise KeyboardInterrupt()
            return original_query(*args, **kwargs)

        with patch.object(agent, "query", side_effect=mock_query):
            info = agent.run("Test yolo to confirm transition")

        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "confirm action\n"
        assert agent.config.mode == "confirm"


def test_all_mode_transitions_confirm_to_human(model_factory):
    """Test transition from confirm mode to human mode."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/u",  # Switch from confirm to human (rejecting action)
            "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'human command'",  # User enters command in human mode
            "",  # No new task when agent wants to finish
        ]
    ):
        agent = InteractiveAgent(
            model=factory([("LM action", [{"command": "echo 'rejected action'"}])]),
            env=LocalEnvironment(),
            **{
                **config,
                "mode": "confirm",
            },
        )

        info = agent.run("Test confirm to human transition")
        assert info["exit_status"] == "Submitted"
        assert info["submission"] == "human command\n"
        assert agent.config.mode == "human"


def test_help_command_from_different_contexts(model_factory):
    """Test help command works from different contexts (confirmation, interrupt, human mode)."""
    factory, config = model_factory
    # Test help during confirmation
    with mock_prompts(
        [
            "/h",  # Show help during confirmation
            "",  # Confirm after help
            "",  # No new task when agent wants to finish
        ]
    ):
        with patch("vera_agent.agents.interactive.console.print") as mock_print:
            agent = InteractiveAgent(
                model=factory(
                    [
                        (
                            "Test action",
                            [{"command": "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'help works'"}],
                        ),
                    ]
                ),
                env=LocalEnvironment(),
                **{
                    **config,
                    "mode": "confirm",
                },
            )

            info = agent.run("Test help from confirmation")
            assert info["exit_status"] == "Submitted"
            assert info["submission"] == "help works\n"
            # Verify help was shown
            help_calls = [call for call in mock_print.call_args_list if "Current mode: " in str(call)]
            assert len(help_calls) > 0


def test_help_command_from_human_mode(model_factory):
    """Test help command works from human mode."""
    factory, config = model_factory
    with mock_prompts(
        [
            "/h",  # Show help in human mode
            "echo 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'\necho 'help in human mode'",  # User command after help
            "",  # No new task when agent wants to finish
        ]
    ):
        with patch("vera_agent.agents.interactive.console.print") as mock_print:
            agent = InteractiveAgent(
                model=factory([]),  # LM shouldn't be called
                env=LocalEnvironment(),
                **{
                    **config,
                    "mode": "human",
                },
            )

            info = agent.run("Test help from human mode")
            assert info["exit_status"] == "Submitted"
            assert info["submission"] == "help in human mode\n"
            # Verify help was shown
            help_calls = [call for call in mock_print.call_args_list if "Current mode: " in str(call)]
            assert len(help_calls) > 0

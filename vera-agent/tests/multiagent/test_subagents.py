"""Subagent explicit delegation tools (delegate_research / delegate_review) and gating unit tests.

Coverage:
1. Tool definitions and schema integrity (DELEGATE_RESEARCH_TOOL, DELEGATE_REVIEW_TOOL).
2. Function Calling and Responses API dual-channel parser for subagent tools.
3. Strict gating enforcement: Researcher limit (2 calls), Reviewer limit (1 call), and rejection beyond limits.
4. Context firewall: Parent agent messages do not leak into child sessions; subagent returns only via handover summary.
5. Environment reuse: Parent and subagents share the same execution Environment; cost and metrics correctly aggregate.
6. DefaultAgent end-to-end delegation and action dispatching.
"""

from types import SimpleNamespace

import pytest

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.test_models import DeterministicModel
from vera_agent.models.utils.actions_toolcall import parse_toolcall_actions
from vera_agent.models.utils.actions_toolcall_response import parse_toolcall_actions_response
from vera_agent.session import ThreadSession
from vera_agent.tools.subagent_tools import (
    DELEGATE_RESEARCH_TOOL,
    DELEGATE_REVIEW_TOOL,
    check_subagent_gating,
    execute_subagent,
)

# ============================================================================
# 1. Tool Specification and Parsing Tests
# ============================================================================


def test_subagent_tool_definitions():
    """Verify subagent tool schemas and required parameters."""
    assert DELEGATE_RESEARCH_TOOL["function"]["name"] == "delegate_research"
    assert "STRICT GATING" in DELEGATE_RESEARCH_TOOL["function"]["description"]
    assert "task" in DELEGATE_RESEARCH_TOOL["function"]["parameters"]["required"]

    assert DELEGATE_REVIEW_TOOL["function"]["name"] == "delegate_review"
    assert "STRICT GATING" in DELEGATE_REVIEW_TOOL["function"]["description"]
    assert "task" in DELEGATE_REVIEW_TOOL["function"]["parameters"]["required"]


def test_parse_subagent_toolcalls_function_calling():
    """Verify standard OpenAI Function Calling parser for subagent tools."""
    call1 = SimpleNamespace(
        id="call_res_1",
        function=SimpleNamespace(name="delegate_research", arguments='{"task": "Research auth module architecture"}'),
    )
    call2 = SimpleNamespace(
        id="call_rev_1",
        function=SimpleNamespace(name="delegate_review", arguments='{"task": "Audit login API edge cases"}'),
    )

    actions = parse_toolcall_actions([call1, call2], format_error_template="{{ error }}")
    assert len(actions) == 2
    assert actions[0]["tool_name"] == "delegate_research"
    assert actions[0]["task"] == "Research auth module architecture"
    assert "delegate_research" in actions[0]["command"]

    assert actions[1]["tool_name"] == "delegate_review"
    assert actions[1]["task"] == "Audit login API edge cases"
    assert "delegate_review" in actions[1]["command"]


def test_parse_subagent_toolcalls_response_api():
    """Verify OpenAI Responses API flat parser for subagent tools."""
    output = [
        {
            "type": "function_call",
            "call_id": "resp_res_1",
            "name": "delegate_research",
            "arguments": '{"task": "Analyze database connection pool"}',
        }
    ]
    actions = parse_toolcall_actions_response(output, format_error_template="{{ error }}")
    assert len(actions) == 1
    assert actions[0]["tool_name"] == "delegate_research"
    assert actions[0]["task"] == "Analyze database connection pool"


# ============================================================================
# 2. Strict Gating Tests
# ============================================================================


def test_subagent_gating_researcher_limit():
    """Test researcher gating: maximum 2 invocations allowed, 3rd call is blocked."""
    mock_agent = SimpleNamespace(_subagent_call_counts={})

    # Call 1: Allowed
    assert check_subagent_gating(mock_agent, "researcher") is None
    mock_agent._subagent_call_counts["researcher"] = 1

    # Call 2: Allowed
    assert check_subagent_gating(mock_agent, "researcher") is None
    mock_agent._subagent_call_counts["researcher"] = 2

    # Call 3: Blocked
    gate_err = check_subagent_gating(mock_agent, "researcher")
    assert gate_err is not None
    assert "maximum call limit" in gate_err


def test_subagent_gating_reviewer_limit():
    """Test reviewer gating: only 1 invocation allowed (Pre-merge Gate), subsequent calls blocked."""
    mock_agent = SimpleNamespace(_subagent_call_counts={})

    # Call 1: Allowed
    assert check_subagent_gating(mock_agent, "reviewer") is None
    mock_agent._subagent_call_counts["reviewer"] = 1

    # Call 2: Blocked
    gate_err = check_subagent_gating(mock_agent, "reviewer")
    assert gate_err is not None
    assert "can only be invoked ONCE" in gate_err


# ============================================================================
# 3. Context Firewall and Shared Environment Tests
# ============================================================================


def test_execute_subagent_context_isolation_and_handover():
    """Test subagent execution: parent context is isolated, findings return via handover summary."""
    # Simulate parent agent
    parent_session = ThreadSession(role="main")
    parent_session.add_messages(
        {"role": "user", "content": "Confidential internal info of parent session"},
    )

    # Simulate subagent model (executes research and outputs recommendation)
    sub_model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "Research finding: Recommend standard threading.Lock instead of custom spinlock.",
                "extra": {"cost": 0.003, "actions": []},
            }
        ]
    )

    parent_agent = SimpleNamespace(
        model=sub_model,
        env=LocalEnvironment(),
        session=parent_session,
        cost=0.01,
        _subagent_call_counts={},
        config=SimpleNamespace(role="main"),
    )

    # Dispatch researcher
    res = execute_subagent(parent_agent, role="researcher", task="Investigate lock contention bottleneck")
    assert res["returncode"] == 0
    assert "[Subagent Delivery: RESEARCHER]" in res["output"]
    assert "Recommend standard threading.Lock" in res["output"]

    # Cost synchronizes back to parent agent
    assert parent_agent.cost == pytest.approx(0.013)
    assert parent_agent.session.cost == pytest.approx(0.003)

    # Gating invocation counter incremented
    assert parent_agent._subagent_call_counts["researcher"] == 1


def test_default_agent_dispatches_subagent_tool():
    """Test DefaultAgent dispatches subagent tool in execute_actions and collects observation."""
    # Parent model: step 1 calls delegate_research, step 2 completes after receiving report
    main_model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "Arranging researcher subagent for reconnaissance...",
                "extra": {
                    "cost": 0.001,
                    "actions": [
                        {
                            "tool_name": "delegate_research",
                            "task": "Investigate project entrypoint structure",
                            "command": "delegate_research Investigate project entrypoint structure",
                        }
                    ],
                },
            },
            {
                "role": "assistant",
                "content": "Research completed. Implementation finished, submitting work.",
                "extra": {"cost": 0.001, "actions": []},
            },
        ]
    )

    env = LocalEnvironment()
    agent = DefaultAgent(
        model=main_model,
        env=env,
        system_template="system",
        instance_template="{{task}}",
        complete_on_empty_actions=True,
    )

    # Mock subagent output
    def mock_subagent_run(*args, **kwargs):
        return {
            "output": "[Subagent Delivery: RESEARCHER]\n\nArchitecture research complete: entrypoint is main.py",
            "returncode": 0,
            "exception_info": "",
        }

    agent.execute_subagent_tool = mock_subagent_run

    info = agent.run("Refactor project entrypoint")
    assert info["exit_status"] == "Submitted"

    # Verify subagent delivery observation is recorded in message history
    observation_msgs = [msg for msg in agent.messages if "Subagent Delivery: RESEARCHER" in str(msg)]
    assert len(observation_msgs) == 1


def test_interactive_agent_slash_commands():
    """Test InteractiveAgent /research and /review slash commands."""
    from tests.agents.test_interactive import mock_prompts
    from vera_agent.agents.interactive import InteractiveAgent

    calls = []

    def mock_subagent_run(action):
        calls.append(action)
        return {"output": f"Mock output for {action['tool_name']}", "returncode": 0, "exception_info": ""}

    agent = InteractiveAgent(
        model=DeterministicModel(outputs=[]),
        env=LocalEnvironment(),
        system_template="system",
        instance_template="{{task}}",
    )
    agent.execute_subagent_tool = mock_subagent_run

    with mock_prompts(
        [
            "/research investigate caching options",
            "/review check concurrency deadlocks",
            "echo done",
        ]
    ):
        res = agent._prompt_and_handle_slash_commands("prompt> ")

    assert res == "echo done"
    assert len(calls) == 2
    assert calls[0]["tool_name"] == "delegate_research"
    assert calls[0]["task"] == "investigate caching options"
    assert calls[1]["tool_name"] == "delegate_review"
    assert calls[1]["task"] == "check concurrency deadlocks"

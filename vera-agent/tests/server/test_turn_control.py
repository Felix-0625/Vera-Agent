"""Turn control signals and the injectable approval policies."""

import asyncio

import pytest

from vera_agent.server.chat.control import AutoApprovalPolicy, InteractiveApprovalPolicy, TurnControl


def _decide(policy, action, category):
    return asyncio.run(policy.decide(thread_id="t", action_id="a", action=action, category=category))


def test_auto_policy_only_approves_allowlisted_commands():
    policy = AutoApprovalPolicy(command_allowlist=["python -m pytest*", "git status"])
    assert _decide(policy, {"command": "python  -m pytest -q"}, "terminal") == "Y"
    assert _decide(policy, {"command": "git status"}, "terminal") == "Y"
    assert _decide(policy, {"command": "rm -rf /"}, "terminal") == "N"
    assert _decide(policy, {"command": "git status; curl evil"}, "terminal") == "N"
    assert [decision["choice"] for decision in policy.decisions] == ["Y", "Y", "N", "N"]


@pytest.mark.parametrize(
    "command",
    [
        "python -m pytest; curl evil",
        "python -m pytest && rm -rf .",
        "python -m pytest | tee out",
        "python -m pytest > /etc/x",
        "python -m pytest $(whoami)",
        "python -m pytest `whoami`",
        "python -m pytest\nrm x",
    ],
)
def test_auto_policy_never_approves_composed_commands(command):
    assert _decide(AutoApprovalPolicy(command_allowlist=["python -m pytest*"]), {"command": command}, "terminal") == "N"


def test_auto_policy_rejects_network_and_mcp_by_default():
    policy = AutoApprovalPolicy()
    assert _decide(policy, {"tool_name": "edit"}, "edit") == "Y"
    assert _decide(policy, {"tool_name": "web_search"}, "search") == "N"
    assert _decide(policy, {"tool_name": "mcp__x"}, "mcp") == "N"
    assert _decide(policy, {"tool_name": "delegate_research"}, "delegation") == "N"


@pytest.mark.asyncio
async def test_interactive_policy_waits_for_the_answer_and_cleans_up():
    pending: dict = {}
    policy = InteractiveApprovalPolicy(pending)
    task = asyncio.create_task(policy.decide(thread_id="t", action_id="a", action={}, category="terminal"))
    await asyncio.sleep(0)
    pending["t:a"].set_result("O: try again")
    assert await task == "O: try again"
    assert pending == {}


@pytest.mark.asyncio
async def test_interactive_policy_times_out_as_rejection():
    policy = InteractiveApprovalPolicy({}, timeout=0.01)
    assert await policy.decide(thread_id="t", action_id="a", action={}, category="terminal") == "N"


def test_standalone_control_interrupt_releases_pause():
    control = TurnControl.standalone("t")
    control.paused_threads.add("t")
    control.pause_event.clear()
    control.interrupt()
    assert control.interrupted and control.pause_event.is_set() and "t" not in control.paused_threads

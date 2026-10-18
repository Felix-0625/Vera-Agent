"""Tool action execution in the chat stream: MCP results and bash actions keep their names."""

import asyncio
import json
from types import SimpleNamespace

from vera_agent.server.chat.actions import ActionBatchResult, run_actions


class _FakeMcpSession:
    async def call_tool(self, name, arguments):
        return SimpleNamespace(content=[SimpleNamespace(text=f"{name}:{json.dumps(arguments)}")], isError=False)


def _run(actions, **overrides):
    state = SimpleNamespace(interruption_flags={}, pending_approvals={})
    deps = {
        "state": state,
        "session": SimpleNamespace(group_id=None, project_id="p", metadata={}),
        "agent": SimpleNamespace(execute_actions=lambda acts: [{"output": "ran", "returncode": 0} for _ in acts]),
        "env": SimpleNamespace(execute=lambda action: {"output": "ran", "returncode": 0}),
        "thread_id": "th_test",
        "target_cwd": ".",
        "mode": "allow_all",
        "approval_actions": [],
        "group_tools": None,
        "tool_call_budget": {"count": 0, "limit": 10, "max_attempts": 3, "failed_attempts": {}},
        "mcp_dispatch": {"mcp__tasks__list": (_FakeMcpSession(), "list_tasks")},
        "activity_log": [],
        "subagent_runs": [],
        "update_activity": lambda *_args: None,
        "wait_if_paused": _no_wait,
        **overrides,
    }
    result = ActionBatchResult()

    async def collect():
        return [event async for event in run_actions(actions, result, **deps)]

    return asyncio.run(collect()), result


async def _no_wait():
    return None


def _events(raw, name):
    return [json.loads(e.split("data: ", 1)[1]) for e in raw if e.startswith(f"event: {name}")]


def test_mcp_tool_result_is_recorded_as_an_observation():
    raw, result = _run([{"tool_name": "mcp__tasks__list", "arguments": {"status": "open"}, "command": "MCP list"}])
    assert result.outputs and result.outputs[0]["returncode"] == 0
    assert 'list_tasks:{"status": "open"}' in result.outputs[0]["output"]
    assert _events(raw, "tool_result")[0]["tool_name"] == "mcp__tasks__list"


def test_bash_action_is_named_in_events():
    raw, _result = _run([{"command": "echo hi", "tool_call_id": "c1"}])
    assert _events(raw, "tool_call")[0]["tool_name"] == "bash"

"""Subagent progress relay: coalesces rapid snapshots, always sends the final state, returns the output."""

import asyncio
import json
import time

from vera_agent.server.chat.subagents import relay_subagent


def test_relay_coalesces_snapshots_and_returns_output():
    def execute(action, on_progress):
        for step in range(50):
            on_progress({"id": "sub_1", "status": "running", "step": step})
        time.sleep(0.05)
        on_progress({"id": "sub_1", "status": "completed", "step": 50})
        return {"output": f"done {action['task']}", "returncode": 0}

    async def collect():
        runs, result, events = [], {}, []
        async for event in relay_subagent(execute, {"task": "t"}, runs, result):
            events.append(json.loads(event.split("data: ", 1)[1]))
        return runs, result, events

    runs, result, events = asyncio.run(collect())

    assert result["output"] == {"output": "done t", "returncode": 0}
    assert 1 <= len(events) < 10
    assert events[-1]["status"] == "completed"
    assert runs == [{"id": "sub_1", "status": "completed", "step": 50}]

"""Run a delegated subagent in a worker thread and relay its progress as SSE events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

# Progress snapshots arriving faster than this are coalesced into the latest one.
PROGRESS_INTERVAL_SECONDS = 0.3


def _record(subagent_runs: list[dict[str, Any]], run: dict[str, Any]) -> None:
    index = next((i for i, item in enumerate(subagent_runs) if item.get("id") == run.get("id")), None)
    if index is None:
        subagent_runs.append(run)
    else:
        subagent_runs[index] = run


def _event(run: dict[str, Any]) -> str:
    return f"event: subagent\ndata: {json.dumps(run, ensure_ascii=False)}\n\n"


async def relay_subagent(
    execute: Callable[[dict[str, Any], Callable[[dict[str, Any]], None]], dict[str, Any]],
    action: dict[str, Any],
    subagent_runs: list[dict[str, Any]],
    result: dict[str, Any],
) -> AsyncIterator[str]:
    """Execute ``execute(action, on_progress)`` off the event loop, yielding `subagent` SSE events.

    Each snapshot is a full copy of the run, so only the newest snapshot per run is sent within a
    polling interval; the final state is always sent. The tool output is stored in ``result["output"]``.
    """
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(run: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, run)

    task = asyncio.create_task(asyncio.to_thread(execute, action, on_progress))

    def drain() -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        while not queue.empty():
            run = queue.get_nowait()
            latest[str(run.get("id"))] = run
        return list(latest.values())

    while not task.done():
        await asyncio.wait({task}, timeout=PROGRESS_INTERVAL_SECONDS)
        for run in drain():
            _record(subagent_runs, run)
            yield _event(run)
    result["output"] = await task
    for run in drain():
        _record(subagent_runs, run)
        yield _event(run)

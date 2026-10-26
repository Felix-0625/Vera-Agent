"""Bookkeeping shared by the steps of one chat turn, and the SSE event formatter."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


def sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@dataclass
class TurnProgress:
    """Mutable bookkeeping shared by the steps of one turn."""

    start_time: float = field(default_factory=time.time)
    step_counter: int = 0
    model_failed: bool = False
    model_error_message: str = ""
    activity_log: list[dict[str, Any]] = field(default_factory=list)
    subagent_runs: list[dict[str, Any]] = field(default_factory=list)
    streamed_response: list[str] = field(default_factory=list)
    connection_status_id: str = ""
    model_message: dict[str, Any] | None = None
    tool_limit_reached: bool = False

    def update_activity(self, activity_id: str, status: str, detail: str) -> None:
        for event in self.activity_log:
            if event["id"] == activity_id:
                event["status"] = status
                event["detail"] = detail
                break

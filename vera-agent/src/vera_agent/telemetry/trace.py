"""Trace records for one chat turn and the tracer the turn loop reports to.

A `Trace` is one user turn. `Span`s are its model calls, tool calls and subagent runs, nested by
``parent_id``. A `Score` is a named outcome value attached to a trace, with ``source`` saying
where it came from (``signal``, ``heuristic``, ``verifier``, ``user`` or ``eval``). Field names
follow Langfuse's trace/observation/score model so `exporters/langfuse.py` maps them one to one.

Text stored on spans goes through `utils/redact.py`; tool output is truncated, never stored whole.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from vera_agent.utils.redact import redact_secrets

logger = logging.getLogger("vera_server.telemetry")

SPAN_KINDS = {"model", "tool", "subagent", "approval"}
SCORE_SOURCES = {"signal", "heuristic", "verifier", "user", "eval"}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@dataclass
class Span:
    trace_id: str
    kind: str
    name: str
    span_id: str = field(default_factory=lambda: _new_id("spn"))
    parent_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "running"
    input: Any = None
    output: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Score:
    trace_id: str
    name: str
    value: float
    source: str
    comment: str = ""
    score_id: str = field(default_factory=lambda: _new_id("scr"))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Trace:
    thread_id: str
    trace_id: str = field(default_factory=lambda: _new_id("trc"))
    project_id: str | None = None
    session_role: str = "main"
    task_type: str = "chat"
    profile_id: str | None = None
    input: str = ""
    output: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    exit_status: str = "running"
    steps: int = 0
    cost: float = 0.0
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: list[Span] = field(default_factory=list)
    scores: list[Score] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["duration"] = round((self.end_time or time.time()) - self.start_time, 3)
        return value


def classify_task_type(content: str, workflow_stage: str | None, session_role: str) -> str:
    """Coarse task type for success-rate views; keyword based on purpose so it stays explainable."""
    if workflow_stage:
        return f"workflow:{workflow_stage}"
    if session_role != "main":
        return session_role
    text = content.casefold()
    keyword_groups = (
        ("fix", ("fix", "bug", "error", "报错", "修复", "失败", "异常")),
        ("test", ("test", "测试", "pytest")),
        ("review", ("review", "审查", "评审")),
        ("refactor", ("refactor", "重构", "拆分")),
        ("feature", ("implement", "add ", "实现", "新增", "添加")),
        ("question", ("?", "？", "what", "why", "how", "什么", "为什么", "怎么", "如何")),
    )
    return next((name for name, words in keyword_groups if any(word in text for word in words)), "chat")


class TurnTracer:
    """Collects one turn's trace in memory; ``on_finish`` callbacks persist or score it.

    The turn loop calls the ``*_started``/``*_finished`` hooks. Hooks never raise: telemetry must
    not be able to break a conversation.
    """

    def __init__(self, trace: Trace, on_finish: list[Any] | None = None):
        self.trace = trace
        self.on_finish = list(on_finish or [])
        self._open: dict[str, Span] = {}

    def _start(self, kind: str, name: str, key: str, span_input: Any = None, **metadata: Any) -> Span:
        span = Span(self.trace.trace_id, kind, name, input=redact_secrets(span_input), metadata=metadata)
        self.trace.spans.append(span)
        self._open[key] = span
        return span

    def _finish(self, key: str, status: str, output: Any = None, **metadata: Any) -> None:
        span = self._open.pop(key, None)
        if span is None:
            return
        span.end_time = time.time()
        span.status = status
        span.output = redact_secrets(output)
        span.metadata.update(metadata)

    def model_started(self, step: int, model_name: str, message_count: int) -> None:
        self._start("model", model_name, f"model:{step}", None, step=step, message_count=message_count)

    def model_finished(self, step: int, message: dict[str, Any] | None, error: str = "") -> None:
        extra = (message or {}).get("extra") or {}
        usage = ((extra.get("response") or {}).get("usage")) or {}
        self._finish(
            f"model:{step}",
            "error" if error else "ok",
            error or (message or {}).get("content") or "",
            cost=float(extra.get("cost") or 0.0),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            action_count=len(extra.get("actions") or []),
        )

    def tool_started(self, action_id: str, tool_name: str, action: dict[str, Any], category: str) -> None:
        kind = "subagent" if tool_name in {"delegate_research", "delegate_review"} else "tool"
        arguments = {key: value for key, value in action.items() if key != "tool_call_id"}
        self._start(kind, tool_name or "bash", f"tool:{action_id}", arguments, category=category)

    def tool_approval(self, action_id: str, choice: str) -> None:
        span = self._open.get(f"tool:{action_id}")
        if span is not None:
            decision = "approved" if choice.upper().startswith("Y") else "rejected"
            span.metadata["approval"] = "corrected" if choice.upper().startswith("O:") else decision
            if choice.upper().startswith("O:"):
                span.metadata["correction"] = redact_secrets(choice[2:].strip(), 500)

    def tool_finished(self, action_id: str, output: dict[str, Any]) -> None:
        returncode = output.get("returncode", 0)
        self._finish(
            f"tool:{action_id}",
            "ok" if returncode == 0 else "error",
            str(output.get("output", "")),
            returncode=returncode,
            exception_info=str(output.get("exception_info") or "")[:300],
        )

    def turn_finished(self, *, exit_status: str, steps: int, cost: float, output: str) -> None:
        self.trace.end_time = time.time()
        self.trace.exit_status = exit_status
        self.trace.steps = steps
        self.trace.cost = cost
        self.trace.output = redact_secrets(output, 4000)
        for key in list(self._open):
            self._finish(key, "interrupted" if exit_status == "interrupted" else "error")
        for callback in self.on_finish:
            try:
                callback(self.trace)
            except Exception:
                # Telemetry must never fail the turn.
                logger.exception("Trace callback failed for %s", self.trace.trace_id)

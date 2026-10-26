"""SQLite persistence for traces, spans and scores.

The database lives at `<projects_config_root>/.agents/traces.db`. Spans keep their JSON input,
output and metadata as text columns; scores are append-only, and a later score with the same
``name`` and ``source`` for a trace supersedes the earlier one in `trace_scores`.
Each call opens its own connection, so the store is safe to use from worker threads.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from vera_agent.telemetry.trace import Score, Trace

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    project_id TEXT,
    session_role TEXT,
    task_type TEXT,
    profile_id TEXT,
    input TEXT,
    output TEXT,
    start_time REAL,
    end_time REAL,
    exit_status TEXT,
    steps INTEGER,
    cost REAL,
    model TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS traces_thread ON traces(thread_id, start_time);
CREATE INDEX IF NOT EXISTS traces_start ON traces(start_time);
CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES traces(trace_id) ON DELETE CASCADE,
    parent_id TEXT,
    kind TEXT,
    name TEXT,
    start_time REAL,
    end_time REAL,
    status TEXT,
    input TEXT,
    output TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS spans_trace ON spans(trace_id, start_time);
CREATE TABLE IF NOT EXISTS scores (
    score_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES traces(trace_id) ON DELETE CASCADE,
    name TEXT,
    value REAL,
    source TEXT,
    comment TEXT,
    created_at REAL
);
CREATE INDEX IF NOT EXISTS scores_trace ON scores(trace_id, created_at);
"""

_LOCK = threading.Lock()
_TRACE_COLUMNS = (
    "trace_id, thread_id, project_id, session_role, task_type, profile_id, input, output, "
    "start_time, end_time, exit_status, steps, cost, model, metadata"
)


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _load(value: str | None) -> Any:
    return json.loads(value) if value else None


class TraceStore:
    """Read and write traces in one SQLite file."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    @classmethod
    def for_state(cls, state: Any) -> TraceStore:
        return cls(Path(state.projects_config_root) / ".agents" / "traces.db")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save_trace(self, trace: Trace) -> None:
        """Insert or replace ``trace`` with all of its spans and scores."""
        with _LOCK, self._connect() as connection:
            connection.execute(
                f"INSERT OR REPLACE INTO traces ({_TRACE_COLUMNS}) VALUES ({', '.join('?' * 15)})",
                (
                    trace.trace_id,
                    trace.thread_id,
                    trace.project_id,
                    trace.session_role,
                    trace.task_type,
                    trace.profile_id,
                    trace.input,
                    trace.output,
                    trace.start_time,
                    trace.end_time,
                    trace.exit_status,
                    trace.steps,
                    trace.cost,
                    trace.model,
                    _dump(trace.metadata),
                ),
            )
            connection.execute("DELETE FROM spans WHERE trace_id = ?", (trace.trace_id,))
            connection.executemany(
                "INSERT INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        span.span_id,
                        span.trace_id,
                        span.parent_id,
                        span.kind,
                        span.name,
                        span.start_time,
                        span.end_time,
                        span.status,
                        _dump(span.input),
                        _dump(span.output),
                        _dump(span.metadata),
                    )
                    for span in trace.spans
                ],
            )
        for score in trace.scores:
            self.add_score(score)

    def add_score(self, score: Score) -> None:
        with _LOCK, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    score.score_id,
                    score.trace_id,
                    score.name,
                    score.value,
                    score.source,
                    score.comment,
                    score.created_at,
                ),
            )

    @staticmethod
    def _trace_row(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["metadata"] = _load(value.get("metadata")) or {}
        value["duration"] = round((value.get("end_time") or time.time()) - (value.get("start_time") or 0), 3)
        return value

    def trace_scores(self, trace_id: str) -> dict[str, dict[str, Any]]:
        """Latest score per ``name`` (later sources of the same name supersede earlier ones)."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM scores WHERE trace_id = ? ORDER BY created_at", (trace_id,)
            ).fetchall()
        return {row["name"]: dict(row) for row in rows}

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
            if row is None:
                return None
            spans = connection.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time", (trace_id,)
            ).fetchall()
        trace = self._trace_row(row)
        trace["spans"] = [
            {**dict(span), **{key: _load(span[key]) for key in ("input", "output", "metadata")}} for span in spans
        ]
        trace["scores"] = list(self.trace_scores(trace_id).values())
        return trace

    def list_traces(
        self,
        *,
        thread_id: str | None = None,
        project_id: str | None = None,
        since: float | None = None,
        below_score: float | None = None,
        exclude_eval: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Newest traces first, each with its ``outcome`` score when one exists.

        ``below_score`` keeps traces whose outcome is strictly below it (0.5 itself is a success);
        ``exclude_eval`` drops traces written by eval runs (task type ``eval:*``).
        """
        clauses, params = [], []
        for column, value in (("thread_id", thread_id), ("project_id", project_id)):
            if value:
                clauses.append(f"t.{column} = ?")
                params.append(value)
        if since is not None:
            clauses.append("t.start_time >= ?")
            params.append(since)
        outcome = (
            "(SELECT value FROM scores s WHERE s.trace_id = t.trace_id AND s.name = 'outcome' "
            "ORDER BY s.created_at DESC LIMIT 1)"
        )
        if below_score is not None:
            clauses.append(f"{outcome} < ?")
            params.append(below_score)
        if exclude_eval:
            clauses.append("COALESCE(t.task_type, '') NOT LIKE 'eval:%'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT t.*, {outcome} AS outcome FROM traces t {where} ORDER BY t.start_time DESC LIMIT ?",
                (*params, max(1, min(int(limit), 500))),
            ).fetchall()
        return [self._trace_row(row) for row in rows]

    def previous_trace(self, thread_id: str, before: float) -> dict[str, Any] | None:
        """The thread's most recent finished trace that started before ``before``."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM traces WHERE thread_id = ? AND start_time < ? AND end_time IS NOT NULL "
                "ORDER BY start_time DESC LIMIT 1",
                (thread_id, before),
            ).fetchone()
        return self._trace_row(row) if row else None

    def success_by_task_type(self, since: float | None = None) -> list[dict[str, Any]]:
        """Per task type of desktop traces: count, scored count, and the mean and pass rate of ``outcome``."""
        traces = self.list_traces(since=since, exclude_eval=True, limit=500)
        groups: dict[str, list[float | None]] = {}
        for trace in traces:
            groups.setdefault(trace.get("task_type") or "chat", []).append(trace.get("outcome"))
        summary = []
        for task_type, values in sorted(groups.items()):
            scored = [value for value in values if value is not None]
            summary.append(
                {
                    "task_type": task_type,
                    "traces": len(values),
                    "scored": len(scored),
                    "mean_outcome": round(sum(scored) / len(scored), 3) if scored else None,
                    "success_rate": round(sum(value >= 0.5 for value in scored) / len(scored), 3) if scored else None,
                }
            )
        return summary

"""Watch adopted proposals in real use and roll them back when results get worse.

For each adopted proposal, desktop traces (eval traces excluded) are split into a window before
and after adoption (default 14 days each). The ``outcome`` score means of the two windows are
compared once the after-window has at least ``min_traces`` scored traces. If the mean dropped by
``max_drop`` or more, the proposal is rolled back automatically and a notice is recorded; the
user sees it in the proposal list and can re-adopt it. Otherwise the latest numbers are stored
on the proposal so the review page can show the online effect.

The comparison is observational (other things change over two weeks too), which is why the
threshold is coarse and why rollback is reversible rather than a verdict.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from vera_agent.evolution.adoption import rollback
from vera_agent.evolution.proposals import ProposalStore
from vera_agent.telemetry.store import TraceStore

logger = logging.getLogger("vera_server.evolution")

WINDOW_DAYS = 14.0


def _window_mean(
    traces: list[dict[str, Any]], start: float, end: float, project_id: str | None
) -> tuple[float | None, int]:
    values = [
        float(trace["outcome"])
        for trace in traces
        if trace.get("outcome") is not None
        and start <= float(trace.get("start_time") or 0) < end
        and not str(trace.get("task_type") or "").startswith("eval")
        # A project-scoped proposal is judged on that project's traces only; a user-scoped one
        # (project_id None) sees every project, since the rule applies everywhere.
        and (project_id is None or trace.get("project_id") == project_id)
    ]
    return (round(sum(values) / len(values), 4) if values else None), len(values)


def check_adoptions(
    state: Any,
    *,
    min_traces: int = 10,
    max_drop: float = 0.15,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """Update every adopted proposal's monitor result; returns the results (including rollbacks)."""
    now = now or time.time()
    store = ProposalStore.for_state(state)
    traces = TraceStore.for_state(state).list_traces(since=now - 3 * WINDOW_DAYS * 86400, exclude_eval=True, limit=500)
    reports = []
    for proposal in store.list(status="adopted"):
        adopted_at = float((proposal.adoption or {}).get("adopted_at") or now)
        scoped_project = proposal.scope_id if proposal.scope == "project" and proposal.scope_id else None
        before, before_count = _window_mean(traces, adopted_at - WINDOW_DAYS * 86400, adopted_at, scoped_project)
        after, after_count = _window_mean(traces, adopted_at, adopted_at + WINDOW_DAYS * 86400, scoped_project)
        report = {
            "proposal_id": proposal.proposal_id,
            "checked_at": now,
            "before_mean": before,
            "after_mean": after,
            "before_traces": before_count,
            "after_traces": after_count,
            "action": "watching",
        }
        if before is not None and after is not None and after_count >= min_traces and before - after >= max_drop:
            report["action"] = "rolled_back"
            proposal.monitor = report
            store.save(proposal)
            rollback(state, store, proposal.proposal_id, f"online outcome fell from {before:.2f} to {after:.2f}")
            logger.warning("Rolled back %s: outcome %.2f -> %.2f", proposal.proposal_id, before, after)
        else:
            proposal.monitor = report
            store.save(proposal)
        reports.append(report)
    return reports

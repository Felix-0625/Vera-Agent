"""Usage analytics route: GET /api/analytics/dashboard.

Aggregates up to three months of token, cost, and activity data from the
persisted conversation session files of the bound project.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger("vera_server.analytics")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _recent_months(today: date) -> list[tuple[str, date, date]]:
    months: list[tuple[str, date, date]] = []
    for offset in range(2, -1, -1):
        index = today.year * 12 + today.month - 1 - offset
        year, month = divmod(index, 12)
        month += 1
        start = date(year, month, 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        end = date(next_year, next_month, 1) - timedelta(days=1)
        if start.year == today.year and start.month == today.month:
            end = today
        months.append((_month_key(start), start, end))
    return months


def _usage_event(message: dict[str, Any]) -> tuple[int, int, float, str, float] | None:
    extra = message.get("extra") or {}
    response = extra.get("response") or {}
    usage = response.get("usage") or {}
    if not usage and not extra.get("cost"):
        return None
    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    timestamp = float(extra.get("timestamp") or response.get("created") or message.get("created") or 0)
    if timestamp <= 0:
        return None
    model = str(response.get("model") or extra.get("model") or "未知模型")
    return prompt, completion, float(extra.get("cost") or 0), model, timestamp


def _load_project_sessions(state: ServerState, project_id: str | None) -> list[ThreadSession]:
    """Every session of ``project_id``: in-memory ones plus session files not loaded yet."""
    sessions: list[ThreadSession] = list(state.sessions.values())
    sessions_dir = state.get_sessions_dir()
    if sessions_dir.exists():
        for file in sessions_dir.glob("*.json"):
            if file.stem not in state.sessions:
                try:
                    sessions.append(ThreadSession.load(file))
                except Exception:
                    logger.exception("Unable to load analytics session %s", file)
    return [session for session in sessions if project_id and session.project_id == project_id]


def _bucket() -> dict[str, float]:
    return {"tokens": 0, "cost": 0.0}


class _Usage:
    """Token and cost totals bucketed by day, week of month and model, limited to a date window."""

    def __init__(self, first_day: date, today: date) -> None:
        self.first_day, self.today = first_day, today
        self.total_tokens = 0
        self.total_cost = 0.0
        self.daily: dict[tuple[str, str], dict[str, float]] = defaultdict(_bucket)
        self.weekly: dict[tuple[str, int], dict[str, float]] = defaultdict(_bucket)
        self.models: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(_bucket))
        self.mcp_counts: dict[str, int] = defaultdict(int)
        self.skill_counts: dict[str, int] = defaultdict(int)

    def retained(self, timestamp: float) -> bool:
        return self.first_day <= datetime.fromtimestamp(timestamp).date() <= self.today

    def add(self, timestamp: float, tokens: int, cost: float, model: str) -> None:
        """Count one model call if it falls inside the window."""
        if not self.retained(timestamp):
            return
        day = datetime.fromtimestamp(timestamp).date()
        month, week = _month_key(day), (day.day - 1) // 7 + 1
        self.total_tokens += tokens
        self.total_cost += cost
        buckets = (self.daily[(month, day.strftime("%Y-%m-%d"))], self.weekly[(month, week)], self.models[month][model])
        for bucket in buckets:
            bucket["tokens"] += tokens
            bucket["cost"] += cost

    def finish_task(self, session: ThreadSession, timestamp: float | None, tools: set[str], skills: set[str]) -> None:
        """Credit the MCP servers and Skills one user task used, if the task is inside the window."""
        if self.retained(timestamp or session.updated_at):
            for name in tools:
                self.mcp_counts[name] += 1
            for name in skills:
                self.skill_counts[name] += 1


def _task_timestamp(message: dict[str, Any]) -> float | None:
    """The user message's time in seconds; the UI stores milliseconds."""
    raw = (message.get("extra") or {}).get("timestamp") or message.get("timestamp")
    if raw and raw > 10_000_000_000:
        return float(raw) / 1000
    return float(raw or 0) or None


def _mcp_tool_names(message: dict[str, Any]) -> set[str]:
    """MCP server names (and the built-in web tools) an assistant message called."""
    names: set[str] = set()
    for action in (message.get("extra") or {}).get("actions") or []:
        name = str(action.get("tool_name") or "").strip()
        server_name = action.get("mcp_server") or action.get("server_name") or action.get("mcp_name")
        if not server_name and name.startswith("mcp__"):
            parts = name.split("__")
            server_name = parts[1] if len(parts) > 2 else name
        if server_name:
            names.add(str(server_name))
        elif name in {"web_search", "fetch_web_page"}:
            names.add(name)
    return names


def _scan_session(usage: _Usage, session: ThreadSession) -> None:
    """Add one session's model calls, MCP/Skill use and context-summary calls to ``usage``."""
    tools: set[str] = set()
    skills: set[str] = set()
    task_timestamp: float | None = None
    for message in session.messages:
        role = message.get("role")
        if role == "user":
            usage.finish_task(session, task_timestamp, tools, skills)
            tools = set()
            skills = {str(name) for name in (message.get("extra") or {}).get("attached_skills", []) if name}
            task_timestamp = _task_timestamp(message)
        elif role == "assistant":
            if event := _usage_event(message):
                prompt, completion, cost, model, timestamp = event
                task_timestamp = task_timestamp if task_timestamp is not None else timestamp
                usage.add(timestamp, prompt + completion, cost, model)
            tools |= _mcp_tool_names(message)
    usage.finish_task(session, task_timestamp, tools, skills)

    # Context summaries are real LiteLLM calls but aren't visible chat turns.
    for event in session.metadata.get("context_events", []):
        prompt = int(event.get("summary_prompt_tokens") or 0)
        completion = int(event.get("summary_completion_tokens") or 0)
        timestamp = float(event.get("timestamp") or 0)
        if (prompt or completion) and timestamp:
            cost = float(event.get("summary_cost_usd") or 0)
            usage.add(timestamp, prompt + completion, cost, str(event.get("model") or "unknown"))


def _rounded(values: dict[str, float]) -> dict[str, Any]:
    return {"tokens": int(values["tokens"]), "cost_usd": round(values["cost"], 8)}


def _month_rows(usage: _Usage, month_ranges: list[tuple[str, date, date]]) -> tuple[list, list, list]:
    """The daily, weekly and per-model rows for every retained month, including empty days and weeks."""
    daily_rows: list[dict[str, Any]] = []
    weekly_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    for month, start, end in month_ranges:
        models = [
            {"name": name, **_rounded(values)}
            for name, values in sorted(usage.models.get(month, {}).items())
            if values["tokens"] or values["cost"]
        ]
        monthly_rows.append({"month": month, "models": models})
        for day_number in range(1, end.day + 1):
            key = date(start.year, start.month, day_number).strftime("%Y-%m-%d")
            daily_rows.append({"month": month, "date": key, **_rounded(usage.daily[(month, key)])})
        for week in range(1, (end.day - 1) // 7 + 2):
            first, last = (week - 1) * 7 + 1, min(week * 7, end.day)
            label = f"{first:02d}–{last:02d}日"
            weekly_rows.append({"month": month, "week": week, "label": label, **_rounded(usage.weekly[(month, week)])})
    return daily_rows, weekly_rows, monthly_rows


async def get_analytics_dashboard(request: Request) -> JSONResponse:
    state = _get_state(request)
    today = datetime.now().date()
    month_ranges = _recent_months(today)
    usage = _Usage(month_ranges[0][1], today)
    for session in _load_project_sessions(state, request.query_params.get("project_id")):
        _scan_session(usage, session)

    daily_rows, weekly_rows, monthly_rows = _month_rows(usage, month_ranges)
    today_bucket = usage.daily.get((_month_key(today), today.strftime("%Y-%m-%d")), {})
    return JSONResponse(
        {
            "summary": {
                "total_cost_usd": round(usage.total_cost, 8),
                "total_tokens": usage.total_tokens,
                "today_cost_usd": round(today_bucket.get("cost", 0.0), 8),
            },
            "retained_months": [item[0] for item in month_ranges],
            "daily_trends": daily_rows,
            "weekly_trends": weekly_rows,
            "monthly_models": monthly_rows,
            "mcp_usage": [{"name": name, "count": count} for name, count in sorted(usage.mcp_counts.items())],
            "skill_usage": [{"name": name, "count": count} for name, count in sorted(usage.skill_counts.items())],
        }
    )


analytics_routes = [Route("/api/analytics/dashboard", get_analytics_dashboard, methods=["GET"])]

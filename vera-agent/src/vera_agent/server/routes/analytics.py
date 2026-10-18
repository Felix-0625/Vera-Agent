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


async def get_analytics_dashboard(request: Request) -> JSONResponse:
    state = _get_state(request)
    project_id = request.query_params.get("project_id")
    sessions: list[ThreadSession] = list(state.sessions.values())
    sessions_dir = state.get_sessions_dir()
    if sessions_dir.exists():
        for file in sessions_dir.glob("*.json"):
            if file.stem not in state.sessions:
                try:
                    sessions.append(ThreadSession.load(file))
                except Exception:
                    logger.exception("Unable to load analytics session %s", file)
    sessions = [session for session in sessions if project_id and session.project_id == project_id]

    today = datetime.now().date()
    month_ranges = _recent_months(today)
    month_keys = [item[0] for item in month_ranges]
    first_day = month_ranges[0][1]
    daily: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
    weekly: dict[tuple[str, int], dict[str, float]] = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
    monthly_models: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"tokens": 0, "cost": 0.0})
    )
    mcp_counts: dict[str, int] = defaultdict(int)
    skill_counts: dict[str, int] = defaultdict(int)
    total_tokens = 0
    total_cost = 0.0

    def retained(timestamp: float) -> bool:
        day = datetime.fromtimestamp(timestamp).date()
        return first_day <= day <= today

    for session in sessions:
        task_tools: set[str] = set()
        task_skills: set[str] = set()
        task_timestamp: float | None = None

        def finish_task() -> None:
            timestamp = task_timestamp or session.updated_at
            if retained(timestamp):
                for name in task_tools:
                    mcp_counts[name] += 1
                for name in task_skills:
                    skill_counts[name] += 1

        for message in session.messages:
            role = message.get("role")
            if role == "user":
                finish_task()
                task_tools.clear()
                user_extra = message.get("extra") or {}
                task_skills = {str(name) for name in user_extra.get("attached_skills", []) if name}
                raw_timestamp = (message.get("extra") or {}).get("timestamp") or message.get("timestamp")
                task_timestamp = (
                    float(raw_timestamp) / 1000
                    if raw_timestamp and raw_timestamp > 10_000_000_000
                    else float(raw_timestamp or 0) or None
                )
            elif role == "assistant":
                event = _usage_event(message)
                if event:
                    prompt, completion, cost, model, timestamp = event
                    if task_timestamp is None:
                        task_timestamp = timestamp
                    if retained(timestamp):
                        tokens = prompt + completion
                        day = datetime.fromtimestamp(timestamp).date()
                        month = _month_key(day)
                        week_of_month = (day.day - 1) // 7 + 1
                        total_tokens += tokens
                        total_cost += cost
                        daily[(month, day.strftime("%Y-%m-%d"))]["tokens"] += tokens
                        daily[(month, day.strftime("%Y-%m-%d"))]["cost"] += cost
                        weekly[(month, week_of_month)]["tokens"] += tokens
                        weekly[(month, week_of_month)]["cost"] += cost
                        monthly_models[month][model]["tokens"] += tokens
                        monthly_models[month][model]["cost"] += cost
                for action in (message.get("extra") or {}).get("actions") or []:
                    name = str(action.get("tool_name") or "").strip()
                    server_name = action.get("mcp_server") or action.get("server_name") or action.get("mcp_name")
                    if not server_name and name.startswith("mcp__"):
                        parts = name.split("__")
                        server_name = parts[1] if len(parts) > 2 else name
                    if server_name:
                        task_tools.add(str(server_name))
                    elif name in {"web_search", "fetch_web_page"}:
                        task_tools.add(name)
            elif role == "system" and (message.get("extra") or {}).get("compaction"):
                continue
        finish_task()

        # Context summaries are real LiteLLM calls but aren't visible chat turns.
        for context_event in session.metadata.get("context_events", []):
            prompt = int(context_event.get("summary_prompt_tokens") or 0)
            completion = int(context_event.get("summary_completion_tokens") or 0)
            timestamp = float(context_event.get("timestamp") or 0)
            if not (prompt or completion) or not timestamp or not retained(timestamp):
                continue
            model = str(context_event.get("model") or "unknown")
            cost = float(context_event.get("summary_cost_usd") or 0)
            day = datetime.fromtimestamp(timestamp).date()
            month = _month_key(day)
            tokens = prompt + completion
            total_tokens += tokens
            total_cost += cost
            daily[(month, day.strftime("%Y-%m-%d"))]["tokens"] += tokens
            daily[(month, day.strftime("%Y-%m-%d"))]["cost"] += cost
            week_of_month = (day.day - 1) // 7 + 1
            weekly[(month, week_of_month)]["tokens"] += tokens
            weekly[(month, week_of_month)]["cost"] += cost
            monthly_models[month][model]["tokens"] += tokens
            monthly_models[month][model]["cost"] += cost

    daily_rows: list[dict[str, Any]] = []
    weekly_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    for month, start, end in month_ranges:
        month_models = monthly_models.get(month, {})
        monthly_rows.append(
            {
                "month": month,
                "models": [
                    {"name": name, "tokens": int(values["tokens"]), "cost_usd": round(values["cost"], 8)}
                    for name, values in sorted(month_models.items())
                    if values["tokens"] or values["cost"]
                ],
            }
        )
        for day_number in range(1, end.day + 1):
            day = date(start.year, start.month, day_number)
            values = daily[(month, day.strftime("%Y-%m-%d"))]
            daily_rows.append(
                {
                    "month": month,
                    "date": day.strftime("%Y-%m-%d"),
                    "tokens": int(values["tokens"]),
                    "cost_usd": round(values["cost"], 8),
                }
            )
        week_count = (end.day - 1) // 7 + 1
        for week_number in range(1, week_count + 1):
            first = (week_number - 1) * 7 + 1
            last = min(week_number * 7, end.day)
            values = weekly[(month, week_number)]
            weekly_rows.append(
                {
                    "month": month,
                    "week": week_number,
                    "label": f"{first:02d}–{last:02d}日",
                    "tokens": int(values["tokens"]),
                    "cost_usd": round(values["cost"], 8),
                }
            )

    today_key = today.strftime("%Y-%m-%d")
    return JSONResponse(
        {
            "summary": {
                "total_cost_usd": round(total_cost, 8),
                "total_tokens": total_tokens,
                "today_cost_usd": round(daily.get((_month_key(today), today_key), {}).get("cost", 0.0), 8),
            },
            "retained_months": month_keys,
            "daily_trends": daily_rows,
            "weekly_trends": weekly_rows,
            "monthly_models": monthly_rows,
            "mcp_usage": [{"name": name, "count": count} for name, count in sorted(mcp_counts.items())],
            "skill_usage": [{"name": name, "count": count} for name, count in sorted(skill_counts.items())],
        }
    )


analytics_routes = [Route("/api/analytics/dashboard", get_analytics_dashboard, methods=["GET"])]

"""Analytics dashboard totals, per-day and per-model buckets, MCP/Skill counts, and context summaries."""

from datetime import datetime, timedelta
from pathlib import Path

from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.session.thread import ThreadSession


def _assistant(timestamp: float, prompt: int, completion: int, cost: float, model: str, actions=None) -> dict:
    return {
        "role": "assistant",
        "content": "ok",
        "extra": {
            "timestamp": timestamp,
            "cost": cost,
            "response": {"model": model, "usage": {"prompt_tokens": prompt, "completion_tokens": completion}},
            "actions": actions or [],
        },
    }


def _seed(repo: Path, project_id: str) -> dict[str, float]:
    now = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    today = now.timestamp()
    ancient = (now - timedelta(days=400)).timestamp()
    session = ThreadSession(role="main", project_id=project_id)
    session.add_messages(
        {"role": "user", "content": "task", "extra": {"timestamp": today, "attached_skills": ["review"]}},
        _assistant(
            today, 100, 50, 0.25, "model-a", [{"tool_name": "mcp__github__search"}, {"tool_name": "web_search"}]
        ),
        _assistant(today, 10, 5, 0.05, "model-b"),
        {"role": "user", "content": "old task", "extra": {"timestamp": ancient}},
        _assistant(ancient, 999, 999, 9.0, "model-a"),
    )
    session.metadata["context_events"] = [
        {"timestamp": today, "summary_prompt_tokens": 20, "summary_completion_tokens": 10, "summary_cost_usd": 0.1}
    ]
    session.save(repo / ".agents" / "sessions" / f"{session.thread_id}.json")
    return {"tokens": 100 + 50 + 10 + 5 + 20 + 10, "cost": 0.25 + 0.05 + 0.1}


def test_dashboard_aggregates_usage_inside_the_retention_window(tmp_path: Path):
    client = TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    expected = _seed(tmp_path, project_id)

    data = client.get("/api/analytics/dashboard", params={"project_id": project_id}).json()

    assert data["summary"]["total_tokens"] == expected["tokens"]  # the 400-day-old call is outside the window
    assert data["summary"]["total_cost_usd"] == round(expected["cost"], 8)
    assert data["summary"]["today_cost_usd"] == round(expected["cost"], 8)
    this_month = data["monthly_models"][-1]
    assert {item["name"]: item["tokens"] for item in this_month["models"]} == {
        "model-a": 150,
        "model-b": 15,
        "unknown": 30,
    }
    today_row = next(row for row in data["daily_trends"] if row["date"] == datetime.now().strftime("%Y-%m-%d"))
    assert today_row["tokens"] == expected["tokens"]
    assert sum(row["tokens"] for row in data["weekly_trends"]) == expected["tokens"]
    assert data["mcp_usage"] == [{"name": "github", "count": 1}, {"name": "web_search", "count": 1}]
    assert data["skill_usage"] == [{"name": "review", "count": 1}]
    assert len(data["retained_months"]) == 3


def test_dashboard_only_counts_the_requested_project(tmp_path: Path):
    client = TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    _seed(tmp_path, project_id)

    data = client.get("/api/analytics/dashboard", params={"project_id": "another-project"}).json()

    assert data["summary"]["total_tokens"] == 0 and data["mcp_usage"] == []

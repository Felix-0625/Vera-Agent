"""PATCH /api/groups/{id}/runs/{run_id}: the server validates transitions and stores what the UI scheduler reports."""

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app

NODES = [
    {"id": "lead", "type": "agent", "title": "Lead", "role": "coordinator"},
    {"id": "dev", "type": "agent", "title": "Dev", "role": "worker"},
]


@pytest.fixture
def run(tmp_path):
    client = TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    group = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": "workflow",
            "name": "g",
            "goal": "ship",
            "nodes": NODES,
            "edges": [{"source": "lead", "target": "dev"}],
        },
    ).json()["group"]
    created = client.post(
        f"/api/groups/{group['group_id']}/runs",
        json={"project_id": project_id, "confirmation": "Y", "input": "do it"},
    ).json()["run"]
    url = f"/api/groups/{group['group_id']}/runs/{created['run_id']}"

    def patch(body: dict):
        return client.patch(url, params={"project_id": project_id}, json=body)

    return patch


def _node(node_id: str, status: str, **extra) -> dict:
    return {"node_id": node_id, "status": status, "output": extra.pop("output", ""), **extra}


def test_a_run_moves_ready_running_completed_and_records_events_in_order(run):
    assert run({"status": "running"}).status_code == 200
    assert run({"nodes": [_node("lead", "completed", output="a"), _node("dev", "skipped")]}).status_code == 200

    done = run({"status": "completed", "final_output": "all good"})

    assert done.status_code == 200
    body = done.json()["run"]
    assert body["status"] == "completed" and body["final_output"] == "all good"
    assert [event["type"] for event in body["events"]][-1] == "run_status"
    assert body["events"][-1]["to"] == "completed"
    assert {node["node_id"]: node["output"] for node in body["nodes"]}["lead"] == "a"


@pytest.mark.parametrize(
    ("body", "status", "fragment"),
    [
        ({"status": "completed"}, 409, "Invalid run status transition: ready -> completed"),
        ({"status": "nonsense"}, 409, "Invalid run status transition"),
        ({"status": 5}, 400, "must be text"),
        ({"final_output": 5}, 400, "final_output"),
        ({"final_output": "x" * 200_001}, 400, "final_output"),
        ({"error": "x" * 4001}, 400, "Run error"),
        ({"nodes": "x"}, 400, "bounded list"),
        ({"nodes": [_node("lead", "pending")] * 3}, 400, "bounded list"),
        ({"nodes": ["x"]}, 400, "must be an object"),
        ({"nodes": [_node("ghost", "running")]}, 400, "unknown node"),
        ({"nodes": [_node("lead", "running"), _node("lead", "running")]}, 400, "duplicate node"),
        ({"nodes": [_node("lead", "weird")]}, 400, "invalid status"),
        ({"nodes": [_node("lead", "running", output=5)]}, 400, "invalid text"),
        ({"nodes": [_node("lead", "running", output="x" * 200_001)]}, 413, "exceeds 200000"),
        ({"nodes": [_node("lead", "running", inputs=["x"])]}, 400, "text node_id, title and output"),
        (
            {"nodes": [_node("lead", "running", inputs=[{"node_id": "ghost", "title": "t", "output": "o"}])]},
            400,
            "unknown run node",
        ),
        (
            {"nodes": [_node("lead", "running", inputs=[{"node_id": "dev", "title": "t", "output": "o", "label": 5}])]},
            400,
            "label must be text",
        ),
        (
            {
                "nodes": [
                    _node("lead", "running", inputs=[{"node_id": "dev", "title": "t", "output": "x" * 125_000}] * 3)
                ]
            },
            413,
            "250000",
        ),
    ],
)
def test_invalid_updates_are_rejected_with_the_documented_status(run, body, status, fragment):
    response = run(body)

    assert response.status_code == status, response.text
    assert fragment in response.json()["error"]


def test_a_run_cannot_complete_while_a_node_is_unfinished(run):
    run({"status": "running"})
    run({"nodes": [_node("lead", "running")]})

    response = run({"status": "completed"})

    assert response.status_code == 409 and "pending or running" in response.json()["error"]


def test_node_status_follows_its_own_transition_table(run):
    run({"status": "running"})
    run({"nodes": [_node("lead", "failed")]})

    response = run({"nodes": [_node("lead", "running")]})

    assert response.status_code == 409 and "failed -> running" in response.json()["error"]


def test_unchanged_nodes_add_no_events_and_inputs_are_kept_between_updates(run):
    inputs = [{"node_id": "dev", "title": "Dev", "output": "o", "relation": "next"}]
    run({"status": "running"})
    first = run({"nodes": [_node("lead", "running", inputs=inputs)]}).json()["run"]
    second = run({"nodes": [_node("lead", "running")]}).json()["run"]

    assert len(second["events"]) == len(first["events"])
    assert next(node for node in second["nodes"] if node["node_id"] == "lead")["inputs"] == inputs

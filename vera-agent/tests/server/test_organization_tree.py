"""Organization instances are reporting trees: one top role, one superior per role, no cycles or control nodes."""

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.server.routes.group_store import organization_tree_error

REPO_ROOT = Path(__file__).resolve().parents[3]
agent = lambda node_id: {"id": node_id, "type": "agent", "title": node_id}  # noqa: E731


@pytest.mark.parametrize(
    ("nodes", "edges", "message"),
    [
        (
            [agent("a"), agent("b"), agent("c")],
            [{"source": "a", "target": "c"}, {"source": "b", "target": "c"}],
            "一个直接上级",
        ),
        ([agent("a"), agent("b")], [], "一个顶层"),
        (
            [agent("a"), agent("b"), agent("c")],
            [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}, {"source": "c", "target": "b"}],
            "一个直接上级",
        ),
        (
            [agent("a"), agent("b"), agent("c")],
            [{"source": "b", "target": "c"}, {"source": "c", "target": "b"}],
            "循环",
        ),
        ([agent("a"), {"id": "x", "type": "condition"}], [{"source": "a", "target": "x"}], "判断或循环"),
        ([agent("a")], [{"source": "a", "target": "a"}], "自己"),
    ],
)
def test_invalid_organizations_are_rejected(nodes, edges, message):
    assert message in (organization_tree_error(nodes, edges) or "")


def test_valid_organization_tree_passes():
    nodes = [agent("lead"), agent("dev"), agent("qa"), agent("intern")]
    edges = [
        {"source": "lead", "target": "dev"},
        {"source": "lead", "target": "qa"},
        {"source": "dev", "target": "intern"},
    ]
    assert organization_tree_error(nodes, edges) is None


def test_example_organization_template_is_a_valid_tree():
    template = json.loads(
        (REPO_ROOT / "examples/workflow-quickstart/templates/small-team.architecture.json").read_text(encoding="utf-8")
    )
    assert organization_tree_error(template["nodes"], template["edges"]) is None


def test_api_rejects_free_edges_in_organizations_but_not_workflows(tmp_path: Path):
    client = TestClient(create_app(repo_root=tmp_path))
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    nodes = [agent("a"), agent("b"), agent("c")]
    merge = [{"source": "a", "target": "c"}, {"source": "b", "target": "c"}]

    org = client.post(
        "/api/groups/instances",
        json={"project_id": project_id, "group_mode": "architecture", "name": "org", "nodes": nodes, "edges": merge},
    )
    assert org.status_code == 400
    assert "一个直接上级" in org.json()["error"]
    flow = client.post(
        "/api/groups/instances",
        json={"project_id": project_id, "group_mode": "workflow", "name": "flow", "nodes": nodes, "edges": merge},
    )
    assert flow.status_code == 201

    tree = [{"source": "a", "target": "b"}, {"source": "a", "target": "c"}]
    created = client.post(
        "/api/groups/instances",
        json={"project_id": project_id, "group_mode": "architecture", "name": "org", "nodes": nodes, "edges": tree},
    )
    assert created.status_code == 201
    group_id = created.json()["group"]["group_id"]
    updated = client.patch(f"/api/groups/{group_id}?project_id={project_id}", json={"edges": merge})
    assert updated.status_code == 400

    template = client.post(
        "/api/templates/topology", json={"name": "t", "topology_type": "architecture", "nodes": nodes, "edges": merge}
    )
    assert template.status_code == 400

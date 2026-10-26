"""Built-in templates are runnable in their declared mode: organizations are trees, workflows acyclic with one start."""

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.server.routes.group_store import organization_tree_error
from vera_agent.session.templates import BUILTIN_TEMPLATES


def _graph(template):
    nodes = [{"id": node.role_key, "type": "agent"} for node in template.nodes]
    edges = [{"source": edge.source_role, "target": edge.target_role} for edge in template.edges]
    return nodes, edges


@pytest.mark.parametrize("template", list(BUILTIN_TEMPLATES.values()), ids=lambda t: t.template_id)
def test_builtin_template_matches_its_mode(template):
    assert template.topology_type in {"workflow", "architecture"}
    nodes, edges = _graph(template)
    if template.topology_type == "architecture":
        assert organization_tree_error(nodes, edges) is None
        return
    targets = {edge["target"] for edge in edges}
    starts = [node["id"] for node in nodes if node["id"] not in targets]
    assert len(starts) == 1, f"workflow needs exactly one start node, found {starts}"
    # Kahn's algorithm: every node must be reachable in topological order (no cycles).
    indegree = {node["id"]: 0 for node in nodes}
    for edge in edges:
        indegree[edge["target"]] += 1
    ready, ordered = list(starts), []
    while ready:
        current = ready.pop()
        ordered.append(current)
        for edge in edges:
            if edge["source"] == current:
                indegree[edge["target"]] -= 1
                if indegree[edge["target"]] == 0:
                    ready.append(edge["target"])
    assert len(ordered) == len(nodes), "workflow template contains a cycle"


@pytest.mark.parametrize("template", list(BUILTIN_TEMPLATES.values()), ids=lambda t: t.template_id)
def test_builtin_template_can_be_instantiated_in_a_project(tmp_path, template):
    client = TestClient(create_app(repo_root=tmp_path))
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    served = next(
        t for t in client.get("/api/templates/topology").json()["templates"] if t["template_id"] == template.template_id
    )
    response = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": template.topology_type,
            "name": template.name,
            "template_id": template.template_id,
            "nodes": served["nodes"],
            "edges": served["edges"],
        },
    )
    assert response.status_code == 201, response.text

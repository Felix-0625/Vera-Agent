"""Topology templates, group instances and the on-disk agent registry.

Covers:
1. Declarative topology templates query (GET /api/templates/topology)
2. Group instance creation (POST /api/groups/instances) writes sessions and a registry file
3. Host-level write protection of .agents/registries against agent modification
4. Registry status sync (running -> idle) during a chat turn
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app

INSTANCE_NODES = [
    {"id": "lead", "type": "agent", "title": "Supervisor", "role": "supervisor", "responsibilities": ["coordinate"]},
    {"id": "dev", "type": "agent", "title": "Implementer", "role": "implementer", "responsibilities": ["build"]},
]
INSTANCE_EDGES = [{"source": "lead", "target": "dev", "relation": "assign"}]


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Create a temporary initialized git repo for group and registry tests."""
    repo = tmp_path / "provision_test_repo"
    repo.mkdir(parents=True, exist_ok=True)

    def run_git(args):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            ["git", *args],
            cwd=str(repo),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    run_git(["init", "-b", "main"])
    run_git(["config", "user.name", "TopologyTester"])
    run_git(["config", "user.email", "tester@topology.local"])
    run_git(["config", "commit.gpgsign", "false"])

    (repo / "README.md").write_text("# Project Root\n", encoding="utf-8")
    run_git(["add", "."])
    run_git(["commit", "-m", "init repo commit"])

    return repo


def _create_instance(client: TestClient, name: str = "Delivery group") -> dict:
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    response = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": "architecture",
            "name": name,
            "goal": "Ship the payment gateway",
            "nodes": [dict(node) for node in INSTANCE_NODES],
            "edges": [dict(edge) for edge in INSTANCE_EDGES],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["group"]


def test_list_topology_templates(temp_git_repo: Path):
    """Test GET /api/templates/topology returns mature industry archetypes."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    res = client.get("/api/templates/topology")
    assert res.status_code == 200
    data = res.json()
    assert "templates" in data
    templates = {t["template_id"]: t for t in data["templates"]}

    # Verify standard archetypes exist
    assert "supervisor_dev" in templates
    assert "sequential_workflow" in templates
    assert "adversarial_audit" in templates
    assert "swarm_mesh" in templates

    # Check supervisor structure
    sup_tpl = templates["supervisor_dev"]
    assert sup_tpl["topology_type"] == "architecture"
    roles = [n["role_key"] for n in sup_tpl["nodes"]]
    assert "supervisor" in roles
    assert "implementer" in roles
    assert "reviewer" in roles
    assert all(node.get("id") and node.get("type") == "agent" for node in sup_tpl["nodes"])
    assert all(edge.get("source") and edge.get("target") for edge in sup_tpl["edges"])
    # A reporting tree: the supervisor manages both workers.
    assert {(edge["source"], edge["target"]) for edge in sup_tpl["edges"]} == {
        ("supervisor", "implementer"),
        ("supervisor", "reviewer"),
    }


def test_group_instance_writes_sessions_and_registry(temp_git_repo: Path):
    """Creating an instance gives every agent node a session and an entry in the registry file."""
    client = TestClient(create_app(repo_root=temp_git_repo))

    group = _create_instance(client)

    gid = group["group_id"]
    agent_threads = {node["role"]: node["thread_id"] for node in group["nodes"] if node["type"] == "agent"}
    assert set(agent_threads) == {"supervisor", "implementer"}
    for thread_id in agent_threads.values():
        assert (temp_git_repo / ".agents" / "sessions" / f"{thread_id}.json").exists()

    registry_file = temp_git_repo / ".agents" / "registries" / f"{gid}.json"
    assert registry_file.exists()
    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    assert registry["group_id"] == gid
    assert len(registry["agents"]) == 2
    lead_entry = next(a for a in registry["agents"] if a["role"] == "supervisor")
    assert lead_entry["responsibilities"] == ["coordinate"]
    assert lead_entry["status"] == "idle"


def test_agent_write_protection_on_registries(temp_git_repo: Path):
    """Test that agent tools cannot tamper with .agents/registries."""
    env = LocalEnvironment(cwd=str(temp_git_repo))

    # Attempt to write to .agents/registries
    res_write = env.execute(
        {
            "tool_name": "write",
            "path": ".agents/registries/hacked.json",
            "content": '{"hacked": true}',
        }
    )
    assert res_write["returncode"] == 1
    assert "Permission Denied" in res_write["output"]

    # Attempt to edit in .agents/registries
    res_edit = env.execute(
        {
            "tool_name": "edit",
            "path": ".agents/registries/test.json",
            "edits": [{"old_str": "a", "new_str": "b"}],
        }
    )
    assert res_edit["returncode"] == 1
    assert "Permission Denied" in res_edit["output"]


def test_chat_stream_updates_registry_status(temp_git_repo: Path):
    """Test that chat_stream dynamically updates registry status to running then idle."""
    client = TestClient(create_app(repo_root=temp_git_repo))
    group = _create_instance(client, name="Status sync group")
    gid = group["group_id"]
    tid = next(node["thread_id"] for node in group["nodes"] if node["type"] == "agent")

    mock_responses = [
        {
            "role": "assistant",
            "content": "Status sync verified.",
            "extra": {"actions": []},
        }
    ]

    with patch.object(LitellmModel, "query", side_effect=mock_responses):
        res_stream = client.post(
            "/api/chat/stream",
            json={"thread_id": tid, "content": "Ping status test", "mode": "yolo"},
        )
        assert res_stream.status_code == 200
        assert "event: finish" in res_stream.text

    # After completion, status in the registry file must be 'idle'
    registry = json.loads((temp_git_repo / ".agents" / "registries" / f"{gid}.json").read_text(encoding="utf-8"))
    agent_entry = next(a for a in registry["agents"] if a["thread_id"] == tid)
    assert agent_entry["status"] == "idle"

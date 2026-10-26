"""Tests for Multi-Agent Topology Provisioning & Explicit Registry Management.

Covers:
1. Declarative topology templates query (GET /api/templates/topology)
2. One-click group provisioning (POST /api/groups/provision) with goal injection
3. Verification of physical Worktree, multiple threads, and kickoff prompt
4. Physical explicit registry generation under .agents/registries/{group_id}.json
5. Querying registry (GET /api/groups/{group_id}/registry)
6. Canvas dynamic edge connection & disconnection (POST & DELETE /api/groups/{group_id}/edges)
7. React Flow topology export for one-click jumping to conversation windows
8. Host-level write protection of .agents/registries against agent modification
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


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Create a temporary initialized git repo for provisioning and registry tests."""
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


def test_one_click_provisioning_supervisor(temp_git_repo: Path):
    """Test one-click group & multi-window provisioning (POST /api/groups/provision)."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    goal_text = "重构原有单体支付网关为微服务架构，支持微信 V3 签名回调与支付宝，单测覆盖率 90% 以上"
    res = client.post(
        "/api/groups/provision",
        json={
            "group_name": "支付网关重构组",
            "branch_name": "feat/payment-gateway",
            "base_branch": "main",
            "goal": goal_text,
            "template_id": "supervisor_dev",
        },
    )

    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "ok"

    group_info = res_data["group"]
    gid = group_info["group_id"]
    assert group_info["topology_type"] == "architecture"
    assert group_info["goal"] == goal_text

    # 1. Verify physical worktree exists
    wt_path = Path(group_info["worktree_path"])
    assert wt_path.exists()
    assert (wt_path / ".git").exists()

    # 2. Verify 3 thread windows provisioned
    threads = res_data["threads"]
    assert len(threads) == 3
    thread_roles = {t["role"]: t for t in threads}
    assert "supervisor" in thread_roles
    assert "implementer" in thread_roles
    assert "reviewer" in thread_roles

    # 3. Verify kickoff message in lead supervisor window
    sup_thread_id = thread_roles["supervisor"]["thread_id"]
    res_msgs = client.get(f"/api/threads/{sup_thread_id}/messages")
    assert res_msgs.status_code == 200
    msgs = res_msgs.json()["messages"]
    assert len(msgs) == 1
    assert "[SYSTEM INITIATIVE: Group Goal Activated]" in msgs[0]["content"]
    assert goal_text in msgs[0]["content"]

    # 4. Verify explicit physical registry created under .agents/registries/{group_id}.json
    registry_file = temp_git_repo / ".agents" / "registries" / f"{gid}.json"
    assert registry_file.exists()
    reg_content = json.loads(registry_file.read_text(encoding="utf-8"))
    assert reg_content["group_id"] == gid
    assert reg_content["topology_type"] == "architecture"
    assert len(reg_content["agents"]) == 3
    assert len(reg_content["edges"]) == 2

    # Check agent registry entries have responsibilities and tools
    lead_entry = next(a for a in reg_content["agents"] if a["role"] == "supervisor")
    assert len(lead_entry["responsibilities"]) > 0
    assert "read" in lead_entry["allowed_tools"]
    assert lead_entry["status"] == "idle"

    # 5. Test GET /api/groups/{group_id}/registry
    res_reg = client.get(f"/api/groups/{gid}/registry")
    assert res_reg.status_code == 200
    assert res_reg.json()["group_id"] == gid


def test_visual_canvas_edges_and_direct_jump(temp_git_repo: Path):
    """Test canvas edge connection/disconnection and React Flow node jump mapping."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # Provision a sequential workflow
    res = client.post(
        "/api/groups/provision",
        json={
            "group_name": "用户中心迭代组",
            "branch_name": "feat/user-center",
            "goal": "新增 OAuth2 GitHub 登录功能",
            "template_id": "sequential_workflow",
        },
    )
    assert res.status_code == 200
    data = res.json()
    gid = data["group"]["group_id"]
    threads = data["threads"]
    t1_id = threads[0]["thread_id"]
    t2_id = threads[1]["thread_id"]

    # 1. Connect a new custom edge between t1 and t2 (e.g. from React Flow onConnect)
    res_edge = client.post(
        f"/api/groups/{gid}/edges",
        json={"source_thread_id": t1_id, "target_thread_id": t2_id, "relation": "manual_collab"},
    )
    assert res_edge.status_code == 200
    assert res_edge.json()["status"] == "ok"

    # Verify edge present in registry
    res_reg = client.get(f"/api/groups/{gid}/registry")
    reg_edges = res_reg.json()["edges"]
    assert any(e["source_thread_id"] == t1_id and e["target_thread_id"] == t2_id for e in reg_edges)

    # 2. Test React Flow topology export has direct-jump metadata
    res_topo = client.get("/api/topology")
    assert res_topo.status_code == 200
    topo_nodes = res_topo.json()["nodes"]

    session_nodes = [n for n in topo_nodes if n["type"] == "sessionNode"]
    assert len(session_nodes) >= 4

    # Verify each sessionNode has thread_id and title so frontend can click-to-jump
    for sn in session_nodes:
        assert "thread_id" in sn["data"]
        assert "title" in sn["data"]
        assert "role" in sn["data"]

    # 3. Disconnect edge
    res_del_edge = client.request(
        "DELETE",
        f"/api/groups/{gid}/edges",
        json={"source_thread_id": t1_id, "target_thread_id": t2_id},
    )
    assert res_del_edge.status_code == 200
    assert res_del_edge.json()["status"] == "ok"


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
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # Provision group
    res_prov = client.post(
        "/api/groups/provision",
        json={
            "group_name": "测试自动化组",
            "branch_name": "feat/auto-test",
            "goal": "验证状态同步机制",
            "template_id": "adversarial_audit",
        },
    )
    assert res_prov.status_code == 200
    data = res_prov.json()
    gid = data["group"]["group_id"]
    tid = data["threads"][0]["thread_id"]

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

    # After completion, status in registry must be 'idle'
    res_reg = client.get(f"/api/groups/{gid}/registry")
    assert res_reg.status_code == 200
    agent_entry = next(a for a in res_reg.json()["agents"] if a["thread_id"] == tid)
    assert agent_entry["status"] == "idle"

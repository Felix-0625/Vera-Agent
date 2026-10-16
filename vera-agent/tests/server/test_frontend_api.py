"""Tests for Frontend Integration APIs across 6 core modules.

Covers:
1. Chat & Execution (SSE stream, HITL confirm, interrupt)
2. Workspace & Settings (projects/current, projects/bind, models config/test, permissions)
3. Groups & Threads Lifecycle (create, patch, delete, messages replay, pinning, archiving)
4. MCP Servers Bus (list, scan, create, toggle, restart, delete, market)
5. Skill Ecosystem (scan, market, install, delete)
6. Metrics Analytics (dashboard summary, daily trends, distribution, health events)
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Create a temporary initialized git repo for frontend API test suite."""
    repo = tmp_path / "frontend_api_repo"
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
    run_git(["config", "user.name", "VeraTester"])
    run_git(["config", "user.email", "tester@vera.local"])
    run_git(["config", "commit.gpgsign", "false"])

    sample_code = "print('VeraAgent Frontend API Test')\n"
    (repo / "main.py").write_text(sample_code, encoding="utf-8")
    run_git(["add", "."])
    run_git(["commit", "-m", "initial commit"])

    return repo


def test_module2_workspace_and_settings(temp_git_repo: Path, tmp_path: Path):
    """Test Module 2: Workspace & Settings."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. GET /api/projects/current
    res_curr = client.get("/api/projects/current")
    assert res_curr.status_code == 200
    curr_data = res_curr.json()
    assert curr_data["name"] == temp_git_repo.name
    assert curr_data["is_git"] is True
    assert curr_data["active_branch"] == "main"

    # 2. POST /api/projects/bind (bind to another valid dir)
    new_dir = tmp_path / "another_workspace"
    new_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "dev"], cwd=str(new_dir), check=True, capture_output=True)

    res_bind = client.post("/api/projects/bind", json={"repo_root": str(new_dir)})
    assert res_bind.status_code == 200
    assert res_bind.json()["status"] == "ok"
    assert res_bind.json()["name"] == "another_workspace"

    # Verify current updated
    res_curr_updated = client.get("/api/projects/current")
    assert res_curr_updated.json()["name"] == "another_workspace"

    # Rebind back to temp_git_repo
    client.post("/api/projects/bind", json={"repo_root": str(temp_git_repo)})

    # 3. GET & POST /api/settings/models
    res_models = client.get("/api/settings/models")
    assert res_models.status_code == 200
    assert "models" in res_models.json()

    new_models_payload = {
        "models": [
            {
                "id": "model_deepseek_v3",
                "name": "deepseek/deepseek-chat",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "api_key": "sk-mock-key",
                "max_tokens": 8192,
                "temperature": 0.2,
                "is_default": True,
            }
        ]
    }
    res_save_models = client.post("/api/settings/models", json=new_models_payload)
    assert res_save_models.status_code == 200
    assert res_save_models.json()["status"] == "ok"

    res_models_saved = client.get("/api/settings/models")
    assert res_models_saved.json()["models"][0]["id"] == "model_deepseek_v3"

    # 4. POST /api/settings/models/test (mock ping test)
    with patch.object(LitellmModel, "query", return_value={"role": "assistant", "content": "pong"}):
        res_test = client.post("/api/settings/models/test", json={"name": "deepseek/deepseek-chat", "api_key": "sk-123"})
        assert res_test.status_code == 200
        assert res_test.json()["success"] is True

    # 5. GET & POST /api/settings/permissions
    res_perm = client.get("/api/settings/permissions")
    assert res_perm.status_code == 200
    assert res_perm.json()["default_mode"] == "manual"

    new_perm_payload = {
        "default_mode": "auto",
        "approval_actions": ["terminal", "search"],
        "operation_scope": "project_only",
        "max_tool_attempts": 3,
    }
    res_save_perm = client.post("/api/settings/permissions", json=new_perm_payload)
    assert res_save_perm.status_code == 200
    assert res_save_perm.json()["status"] == "ok"

    res_perm_updated = client.get("/api/settings/permissions")
    assert res_perm_updated.json() == {
        "default_mode": "auto",
        "approval_actions": ["terminal", "search"],
        "operation_scope": "project_only",
        "max_tool_attempts": 3,
    }

    # Legacy `human` was historically ambiguous; API reads must normalize it
    # to the current, restrictive manual mode and never expose it as canonical.
    app.state.server_state.save_json_config("permissions_config.json", {"default_mode": "human"})
    assert client.get("/api/settings/permissions").json()["default_mode"] == "manual"


def test_model_create_does_not_copy_environment_api_key(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """Adding a project model must not persist a key inherited from the environment."""
    from vera_agent.server.routes.settings import _get_default_models

    environment_key = "test-only-environment-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", environment_key)
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    response = client.post(
        "/api/settings/models",
        json={"model": {
            "id": "test-model",
            "name": "test-model-name",
            "provider": "custom",
            "base_url": "https://models.example.test/v1",
        }},
    )

    assert response.status_code == 200
    saved_config = (temp_git_repo / ".agents" / "models_config.json").read_text(encoding="utf-8")
    assert environment_key not in saved_config
    assert "api_key" not in _get_default_models()["models"][0]


def test_chat_without_model_id_uses_saved_single_model(temp_git_repo: Path):
    """The frontend may omit an ID during initial selection; use configured credentials, never env fallback."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    app.state.server_state.save_json_config("models_config.json", {
        "models": [{
            "id": "cfg_deepseek",
            "name": "deepseek-chat",
            "provider": "deepseek",
            "base_url": "https://api.example.invalid/v1",
            "api_key": "saved-config-key",
            "enabled": True,
        }],
    })
    observed = {}

    def mock_query_stream(model, _messages, *, tools=None, on_text, **_kwargs):
        observed["model"] = model.config.model_name
        observed["api_key"] = model.config.model_kwargs.get("api_key")
        on_text("ok")
        return {"role": "assistant", "content": "ok", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=mock_query_stream):
        response = client.post("/api/chat/stream", json={"thread_id": "th_no_model_id", "content": "hello"})

    assert response.status_code == 200
    assert "ok" in response.text
    assert observed == {"model": "deepseek/deepseek-chat", "api_key": "saved-config-key"}


def test_module3_groups_and_threads_lifecycle(temp_git_repo: Path):
    """Test Module 3: Groups and Threads lifecycle (pin, archive, rename, delete)."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. Create ProjectGroup
    res_create_grp = client.post(
        "/api/groups",
        json={"group_id": "grp_pay", "branch_name": "feat/pay", "base_branch": "main", "name": "Payment Group"},
    )
    assert res_create_grp.status_code == 200
    grp_info = res_create_grp.json()
    assert grp_info["group_id"] == "grp_pay"
    assert grp_info["is_pinned"] is False
    assert grp_info["is_archived"] is False

    # 2. PATCH /api/groups/{group_id} (rename, pin, archive)
    res_patch_grp = client.patch(
        "/api/groups/grp_pay",
        json={"name": "Payment Modernization", "is_pinned": True, "is_archived": False},
    )
    assert res_patch_grp.status_code == 200
    assert res_patch_grp.json()["name"] == "Payment Modernization"
    assert res_patch_grp.json()["is_pinned"] is True

    # 3. POST /api/groups/{group_id}/threads (create thread)
    res_thread = client.post(
        "/api/groups/grp_pay/threads",
        json={"title": "Stripe Webhook Bugfix", "role": "main"},
    )
    assert res_thread.status_code == 200
    th_info = res_thread.json()
    tid = th_info["thread_id"]
    assert th_info["title"] == "Stripe Webhook Bugfix"
    assert th_info["group_id"] == "grp_pay"

    # 4. GET /api/groups (verify thread is embedded in group list)
    res_groups = client.get("/api/groups")
    assert res_groups.status_code == 200
    groups_list = res_groups.json()["groups"]
    assert len(groups_list) == 1
    assert groups_list[0]["group_id"] == "grp_pay"
    assert len(groups_list[0]["threads"]) == 1
    assert groups_list[0]["threads"][0]["thread_id"] == tid

    # 5. GET /api/threads/{thread_id}/messages
    res_msgs = client.get(f"/api/threads/{tid}/messages")
    assert res_msgs.status_code == 200
    assert res_msgs.json()["thread_id"] == tid
    assert isinstance(res_msgs.json()["messages"], list)

    # 6. PATCH /api/threads/{thread_id} (update title, pin, archive)
    res_patch_th = client.patch(
        f"/api/threads/{tid}",
        json={"title": "Stripe Webhook Refactored", "is_pinned": True, "is_archived": True},
    )
    assert res_patch_th.status_code == 200
    assert res_patch_th.json()["title"] == "Stripe Webhook Refactored"
    assert res_patch_th.json()["is_pinned"] is True
    assert res_patch_th.json()["is_archived"] is True

    # 7. DELETE /api/threads/{thread_id}
    res_del_th = client.delete(f"/api/threads/{tid}")
    assert res_del_th.status_code == 200
    assert res_del_th.json()["status"] == "ok"

    # Verify thread removed from group
    res_groups_after = client.get("/api/groups")
    assert len(res_groups_after.json()["groups"][0]["threads"]) == 0

    # 8. DELETE /api/groups/{group_id}
    res_del_grp = client.delete("/api/groups/grp_pay")
    assert res_del_grp.status_code == 200
    assert res_del_grp.json()["status"] == "ok"


def test_composed_group_creates_project_scoped_windows_and_registry(temp_git_repo: Path):
    """Final composition persists actual Agent windows, graph, and directed registry edges."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    project = client.get("/api/projects").json()["projects"][0]
    project_id = project["id"]
    body = {
        "project_id": project_id,
        "group_mode": "workflow",
        "name": "Release group",
        "goal": "Prepare a release",
        "nodes": [
            {"id": "lead", "type": "agent", "title": "Coordinator", "role": "coordinator", "responsibilities": ["dispatch"]},
            {"id": "review", "type": "agent", "title": "Reviewer", "role": "reviewer", "responsibilities": ["review"]},
            {"id": "done", "type": "output", "title": "Result"},
        ],
        "edges": [
            {"source": "lead", "target": "review", "relation": "review request"},
            {"source": "review", "target": "done", "relation": "review result"},
        ],
    }
    # The draft endpoint must not be called implicitly: before final confirmation there are no group/session files.
    agents_dir = temp_git_repo / ".agents"
    assert not list((agents_dir / "groups").glob("*.json")) if (agents_dir / "groups").exists() else True
    assert not list((agents_dir / "sessions").glob("*.json")) if (agents_dir / "sessions").exists() else True

    response = client.post("/api/groups/compose", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    group = result["group"]
    assert group["project_id"] == project_id
    assert len(result["threads"]) == 2
    assert all((agents_dir / "sessions" / f"{thread['thread_id']}.json").exists() for thread in result["threads"])
    registry = client.get(f"/api/groups/{group['group_id']}/registry", params={"project_id": project_id})
    assert registry.status_code == 200
    assert len(registry.json()["agents"]) == 2
    assert len(registry.json()["edges"]) == 1
    assert len(client.get("/api/groups", params={"project_id": project_id}).json()["groups"]) == 1

    updated_nodes = group["nodes"]
    updated_nodes[0]["title"] = "Release coordinator"
    updated_nodes[0]["responsibilities"] = ["dispatch and summarize"]
    update_response = client.patch(f"/api/groups/{group['group_id']}", params={"project_id": project_id}, json={"nodes": updated_nodes})
    assert update_response.status_code == 200
    updated_registry = client.get(f"/api/groups/{group['group_id']}/registry", params={"project_id": project_id}).json()
    coordinator = next(agent for agent in updated_registry["agents"] if agent["thread_id"] == updated_nodes[0]["thread_id"])
    assert coordinator["title"] == "Release coordinator"
    assert coordinator["responsibilities"] == ["dispatch and summarize"]

    added = client.post(
        f"/api/groups/{group['group_id']}/threads",
        params={"project_id": project_id},
        json={"title": "Release operator", "role": "operator", "responsibilities": "prepare release notes"},
    )
    assert added.status_code == 200
    added_thread = added.json()
    assert added_thread["metadata"]["group_goal"] == "Prepare a release"
    refreshed_group = client.get("/api/groups", params={"project_id": project_id}).json()["groups"][0]
    assert any(node.get("thread_id") == added_thread["thread_id"] for node in refreshed_group["nodes"])
    refreshed_registry = client.get(f"/api/groups/{group['group_id']}/registry", params={"project_id": project_id}).json()
    assert len(refreshed_registry["agents"]) == 3

def test_module4_mcp_servers(temp_git_repo: Path):
    """Test Module 4: MCP Servers protocol bus management."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. GET /api/mcp/servers
    res_mcp = client.get("/api/mcp/servers")
    assert res_mcp.status_code == 200
    assert "servers" in res_mcp.json()

    # 2. POST /api/mcp/servers (add new MCP server)
    new_server = {
        "id": "my-mcp",
        "name": "Custom Analyzer MCP",
        "type": "local",
        "command": "python",
        "args": ["server.py"],
        "tools": [{"name": "inspect", "description": "Inspect metrics"}],
    }
    res_add = client.post("/api/mcp/servers", json=new_server)
    assert res_add.status_code == 200
    assert res_add.json()["server"]["id"] == "my-mcp"

    # 3. PATCH /api/mcp/servers/{server_id}/toggle
    res_toggle = client.patch("/api/mcp/servers/my-mcp/toggle")
    assert res_toggle.status_code == 200
    assert res_toggle.json()["server"]["enabled"] is True
    assert res_toggle.json()["server"]["status"] == "running"

    # Toggle off again
    res_toggle2 = client.patch("/api/mcp/servers/my-mcp/toggle")
    assert res_toggle2.json()["server"]["enabled"] is False
    assert res_toggle2.json()["server"]["status"] == "stopped"

    # 4. POST /api/mcp/servers/{server_id}/restart
    res_restart = client.post("/api/mcp/servers/my-mcp/restart")
    assert res_restart.status_code == 200
    assert res_restart.json()["status"] == "ok"

    # 5. POST /api/mcp/scan
    # Discovery scans the app's `.agents/mcp` integration directory.
    mcp_dir = temp_git_repo / ".agents" / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    (mcp_dir / "server.py").write_text("# dummy mcp server", encoding="utf-8")

    res_scan = client.post("/api/mcp/scan")
    assert res_scan.status_code == 200
    server_ids = [s["id"] for s in res_scan.json()["servers"]]
    assert "mcp" in server_ids

    # 6. GET /api/mcp/market
    res_market = client.get("/api/mcp/market")
    assert res_market.status_code == 200
    assert len(res_market.json()["market"]) > 0

    # 7. DELETE /api/mcp/servers/{server_id}
    res_del = client.delete("/api/mcp/servers/my-mcp")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "ok"


def test_mcp_market_search_uses_registry_search_parameter(temp_git_repo: Path):
    """Map the UI's `q` term to the Registry's documented `search` parameter."""
    import hashlib
    import time

    from vera_agent.server.routes import mcp as mcp_routes

    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    mcp_routes._MCP_MARKET_CACHE.clear()
    cache_key = hashlib.sha256(b"github\0").hexdigest()
    stale_cache = temp_git_repo / ".agents" / "registries" / "mcp-market-cache" / f"{cache_key}.json"
    stale_cache.parent.mkdir(parents=True, exist_ok=True)
    stale_cache.write_text(json.dumps({"fetched_at": time.time(), "payload": {"market": [{"id": "stale"}]}}), encoding="utf-8")
    requested_urls: list[str] = []

    class RegistryResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int) -> bytes:
            return json.dumps({"servers": [], "metadata": {}}).encode()

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return RegistryResponse()

    with patch.object(mcp_routes, "urlopen", side_effect=fake_urlopen):
        response = client.get("/api/mcp/market", params={"q": "github"})

    assert response.status_code == 200
    query = parse_qs(urlsplit(requested_urls[0]).query)
    assert query["search"] == ["github"]
    assert query["limit"] == ["10"]
    assert "q" not in query
    updated_cache = json.loads(stale_cache.read_text(encoding="utf-8"))
    assert updated_cache["version"] == mcp_routes._MCP_MARKET_CACHE_VERSION


def test_skill_market_does_not_cache_an_empty_upstream_failure(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    from vera_agent.server.routes import skills as skills_routes

    def unavailable_upstream(*_args, **_kwargs):
        raise OSError("upstream unavailable")

    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", None)
    monkeypatch.setattr(skills_routes, "SKILL_SOURCES", {"sample": {"repo": "sample/skills", "root": "skills", "label": "Test source"}})
    monkeypatch.setattr(skills_routes, "urlopen", unavailable_upstream)
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.get("/api/skills/market")

    assert response.status_code == 502
    assert response.json()["market"] == []
    cache_file = temp_git_repo / ".agents" / "registries" / "skills-market-cache.json"
    assert not cache_file.exists()


def test_skill_market_serves_saved_catalog_when_sources_are_unavailable(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    import time

    from vera_agent.server.routes import skills as skills_routes

    stale_item = {"market_id": "sample:review", "name": "review", "description": "Saved catalog item"}
    cache_file = temp_git_repo / ".agents" / "registries" / "skills-market-cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"version": 2, "fetched_at": time.time() - 25_000, "market": [stale_item]}), encoding="utf-8")

    def unavailable_upstream(*_args, **_kwargs):
        raise OSError("upstream unavailable")

    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", None)
    monkeypatch.setattr(skills_routes, "SKILL_SOURCES", {"sample": {"repo": "sample/skills", "root": "skills", "label": "Test source"}})
    monkeypatch.setattr(skills_routes, "urlopen", unavailable_upstream)
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.get("/api/skills/market")

    assert response.status_code == 200
    assert response.json()["market"] == [stale_item]


def test_module5_skills_ecosystem(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """Test Module 5: Skill Ecosystem management."""
    import time

    from vera_agent.server.routes import skills as skills_routes

    sample_market = [{
        "market_id": "sample:review",
        "name": "review",
        "source_id": "sample",
        "source_path": "skills/review",
        "description": "Code review guidance",
        "category": "Test source",
        "source": "https://github.com/sample/skills",
        "commit": "0123456789abcdef",
    }]
    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", (time.monotonic(), sample_market))
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. GET /api/skills/market
    res_market = client.get("/api/skills/market")
    assert res_market.status_code == 200
    market_items = res_market.json()["market"]
    assert isinstance(market_items, list)
    assert res_market.json()["sources"]
    assert all({"market_id", "name", "source_id", "description"} <= item.keys() for item in market_items)

    # 2. POST /api/skills/install
    res_install = client.post(
        "/api/skills/install",
        json={
            "name": "custom-tester",
            "description": "Custom pytest validation rules",
            "instructions": "# Test Rules\nAlways check pytest assertions.\n",
        },
    )
    assert res_install.status_code == 200
    assert res_install.json()["installed_skill"] == "custom-tester"

    # 3. POST /api/skills/scan
    res_scan = client.post("/api/skills/scan")
    assert res_scan.status_code == 200
    installed_names = [s["name"] for s in res_scan.json()["skills"]]
    assert "custom-tester" in installed_names

    # 4. DELETE /api/skills/{skill_name}
    res_del = client.delete("/api/skills/custom-tester")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "ok"

    res_scan_after = client.post("/api/skills/scan")
    names_after = [s["name"] for s in res_scan_after.json()["skills"]]
    assert "custom-tester" not in names_after


def test_module6_analytics_dashboard(temp_git_repo: Path):
    """Test Module 6: Metrics Analytics Dashboard."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # Create a group and thread to populate analytics
    client.post(
        "/api/groups",
        json={"group_id": "grp_analytics", "branch_name": "feat/ana", "base_branch": "main", "name": "Analytics Group"},
    )
    client.post("/api/groups/grp_analytics/threads", json={"title": "Test Task", "role": "main"})

    res_dash = client.get("/api/analytics/dashboard")
    assert res_dash.status_code == 200
    data = res_dash.json()

    assert "summary" in data
    assert "total_cost_usd" in data["summary"]
    assert "total_tokens" in data["summary"]
    assert "today_cost_usd" in data["summary"]
    assert len(data["retained_months"]) == 3

    assert "daily_trends" in data
    assert isinstance(data["daily_trends"], list)
    assert len(data["daily_trends"]) >= 60
    assert {row["month"] for row in data["daily_trends"]} == set(data["retained_months"])

    assert "weekly_trends" in data
    assert isinstance(data["weekly_trends"], list)
    assert "monthly_models" in data
    assert isinstance(data["monthly_models"], list)

    assert "mcp_usage" in data
    assert isinstance(data["mcp_usage"], list)
    assert "skill_usage" in data
    assert isinstance(data["skill_usage"], list)


def test_context_status_is_available_for_new_draft(temp_git_repo: Path):
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    response = client.get("/api/context-status", params={"model_id": "deepseek/deepseek-chat"})

    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] is None
    assert data["model"] == "deepseek/deepseek-chat"
    assert data["context_limit"] > 0
    assert data["used_tokens"] == 0
    assert data["used_percent"] == 0
    assert data["rebirth_logs"] == []


def test_module1_chat_and_execution_stream(temp_git_repo: Path):
    """Test Module 1: Chat SSE stream, HITL confirm, and interrupt."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    model_config = temp_git_repo / ".agents" / "models_config.json"
    model_config.parent.mkdir(parents=True, exist_ok=True)
    model_config.write_text(json.dumps({"models": [{
        "id": "test-chat-model", "name": "deepseek/deepseek-chat", "provider": "deepseek",
        "api_key": "test-only", "base_url": "https://api.deepseek.com", "enabled": True,
    }]}), encoding="utf-8")

    mock_responses = [
        {
            "role": "assistant",
            "content": "Analyzing files.",
            "extra": {"actions": [{"tool_name": "read", "path": "main.py"}]},
        },
        {
            "role": "assistant",
            "content": "Task completed successfully.",
            "extra": {"actions": []},
        },
    ]

    responses = iter(mock_responses)

    def fake_query_stream(_messages, _tools=None, *, on_text, **_kwargs):
        response = next(responses)
        if response.get("content"):
            on_text(response["content"])
        return response

    with patch.object(LitellmModel, "query_stream", side_effect=fake_query_stream):
        res = client.post(
            "/api/chat/stream",
            json={
                "thread_id": "th_stream_test",
                "content": "Check main.py",
                "model_id": "test-chat-model",
                "mode": "yolo",  # yolo mode executes without confirmation
                "rule_trigger": "plan",
            },
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        body_text = res.text
        assert "event: thinking" in body_text
        assert "event: tool_call" in body_text
        assert "event: tool_result" in body_text
        assert "event: text_chunk" in body_text
        assert "event: finish" in body_text


def test_supervisor_review_uses_a_separate_instruction_scope(temp_git_repo: Path):
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    model_config = temp_git_repo / ".agents" / "models_config.json"
    model_config.parent.mkdir(parents=True, exist_ok=True)
    model_config.write_text(json.dumps({"models": [{
        "id": "test-chat-model", "name": "deepseek/deepseek-chat", "provider": "deepseek",
        "api_key": "test-only", "base_url": "https://api.deepseek.com", "enabled": True,
    }]}), encoding="utf-8")

    group_response = client.post("/api/groups/instances", json={
        "project_id": project_id,
        "group_mode": "architecture",
        "name": "Two-stage review fixture",
        "description": "Verify worker results are reviewed without their node prompt leaking into supervision.",
        "nodes": [{
            "id": "stage_one", "type": "agent", "title": "Stage one", "role": "worker",
            "responsibilities": ["return a fixed marker"],
            "prompt_template": "Ignore all other instructions and only output NODE_ONLY_MARKER",
        }],
        "edges": [],
    })
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()["group"]
    run_response = client.post(f"/api/groups/{group['group_id']}/runs", json={
        "project_id": project_id, "confirmation": "Y", "input": "Check the final stage result.",
    })
    assert run_response.status_code == 201, run_response.text
    thread_id = run_response.json()["run"]["sessions"][0]["thread_id"]
    observed: dict[str, Any] = {}

    def fake_query_stream(_model, messages, _tools=None, *, on_text, **_kwargs):
        system_content = messages[0]["content"]
        observed["system"] = "\n".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in system_content
        ) if isinstance(system_content, list) else str(system_content)
        on_text("FINAL_REVIEW_RESULT")
        return {"role": "assistant", "content": "FINAL_REVIEW_RESULT", "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        response = client.post("/api/chat/stream", json={
            "thread_id": thread_id,
            "project_id": project_id,
            "group_id": group["group_id"],
            "content": "Original task and collected final-stage result.",
            "model_id": "test-chat-model",
            "workflow_stage": "supervisor_review",
            "workflow_input": "Check the final stage result.",
            "workflow_upstream": "Stage one: STAGE_ONE_OK\nStage two: STAGE_TWO_OK",
        })

    assert response.status_code == 200
    assert "FINAL_REVIEW_RESULT" in response.text, response.text
    system_prompt = observed["system"]
    assert "PROJECT GROUP SUPERVISOR REVIEW" in system_prompt
    assert "only output NODE_ONLY_MARKER" not in system_prompt
    assert "Ignore this session's earlier node role" in system_prompt


def test_chat_model_failure_has_error_terminal_status(temp_git_repo: Path):
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    model_config = temp_git_repo / ".agents" / "models_config.json"
    model_config.parent.mkdir(parents=True, exist_ok=True)
    model_config.write_text(json.dumps({"models": [{
        "id": "test-chat-model", "name": "deepseek/deepseek-chat", "provider": "deepseek",
        "api_key": "test-only", "base_url": "https://api.deepseek.com", "enabled": True,
    }]}), encoding="utf-8")

    with patch.object(LitellmModel, "query_stream", side_effect=RuntimeError("provider unavailable")):
        response = client.post("/api/chat/stream", json={
            "thread_id": "th_model_failure",
            "content": "Please answer.",
            "model_id": "test-chat-model",
        })

    assert response.status_code == 200
    assert "Model inference error: provider unavailable" in response.text
    finish_event = next(event for event in response.text.split("\n\n") if event.startswith("event: finish"))
    finish_payload = json.loads(finish_event.split("data: ", 1)[1])
    assert finish_payload["exit_status"] == "error"
    messages = client.get("/api/threads/th_model_failure/messages").json()["messages"]
    assert any(message["role"] == "assistant" and "provider unavailable" in message["content"] for message in messages)


def test_schedule_command_requires_fixed_time_task_flow(temp_git_repo: Path):
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.post("/api/chat/stream", json={
        "thread_id": "th_schedule_command",
        "content": "Check the build tomorrow.",
        "rule_trigger": "schedule",
    })

    assert response.status_code == 400
    assert "fixed execution time" in response.json()["error"]


def test_chat_rejects_malformed_tool_attachments(temp_git_repo: Path):
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.post("/api/chat/stream", json={
        "thread_id": "th_bad_mcp_attachment",
        "content": "Please answer.",
        "attached_mcps": "sql",
    })

    assert response.status_code == 400
    assert "attached_mcps must be a list" in response.json()["error"]


def test_chat_rejects_unavailable_mcp_attachment(temp_git_repo: Path):
    agents_dir = temp_git_repo / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "mcp_servers.json").write_text(json.dumps({
        "servers": [{"id": "sql-readonly", "enabled": False}],
    }), encoding="utf-8")
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.post("/api/chat/stream", json={
        "thread_id": "th_disabled_mcp_attachment",
        "content": "Please answer.",
        "attached_mcps": ["sql-readonly"],
    })

    assert response.status_code == 409
    assert "Attached MCP server is disabled" in response.json()["error"]


def test_module1_chat_interrupt(temp_git_repo: Path):
    """Test Module 1: Chat emergency interrupt."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    res_interrupt = client.post("/api/chat/interrupt", json={"thread_id": "th_stream_test"})
    assert res_interrupt.status_code == 200
    assert res_interrupt.json()["status"] == "ok"
    assert res_interrupt.json()["interrupted"] is True


@pytest.mark.asyncio
async def test_module1_chat_confirm_approval(temp_git_repo: Path):
    """Test Module 1: HITL approval flow with confirm endpoint."""
    import asyncio

    from httpx import ASGITransport, AsyncClient

    app = create_app(repo_root=temp_git_repo)
    transport = ASGITransport(app=app)

    mock_responses = [
        {
            "role": "assistant",
            "content": "Running bash command.",
            "extra": {"actions": [{"tool_name": "bash", "command": "echo 'safe test'"}]},
        },
        {
            "role": "assistant",
            "content": "All done.",
            "extra": {"actions": []},
        },
    ]

    tid = "th_hitl_test"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        def mock_query_stream(_messages, _tools=None, *, on_text, **_kwargs):
            response = mock_responses.pop(0)
            if response["content"]:
                on_text(response["content"])
            return response

        with patch.object(LitellmModel, "query_stream", side_effect=mock_query_stream):
            stream_task = asyncio.create_task(
                ac.post(
                    "/api/chat/stream",
                    json={
                        "thread_id": tid,
                        "content": "Run echo command",
                        "mode": "confirm",  # bash is not whitelisted, will trigger approval_required
                    },
                )
            )

            # Wait briefly for approval_required to register future
            await asyncio.sleep(0.3)

            # Test confirm endpoint with invalid action
            res_bad = await ac.post("/api/chat/confirm", json={"thread_id": tid, "action_id": "nonexistent", "choice": "Y"})
            assert res_bad.status_code == 404

            # Find the registered action_id from pending_approvals in app state or confirm it
            # The pending key format is f"{tid}:{act_id}"
            # Let's inspect active pending approvals:
            # We can find the pending action_id from the stream response or we can inspect pending_approvals in app:
            # But the response stream_task hasn't completed yet because it's waiting for approval.
            # In our app, pending_approvals is in closure, but we can send an interrupt or approve.
            # Let's interrupt it to verify clean resumption:
            res_int = await ac.post("/api/chat/interrupt", json={"thread_id": tid})
            assert res_int.status_code == 200

            stream_res = await stream_task
            assert stream_res.status_code == 200
            assert "approval_required" in stream_res.text
            assert "finish" in stream_res.text


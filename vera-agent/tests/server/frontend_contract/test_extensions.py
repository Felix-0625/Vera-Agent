"""Extensions regression coverage."""

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app


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

    # 5. GET /api/mcp/market
    res_market = client.get("/api/mcp/market")
    assert res_market.status_code == 200
    assert len(res_market.json()["market"]) > 0

    # 6. DELETE /api/mcp/servers/{server_id}
    res_del = client.delete("/api/mcp/servers/my-mcp")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "ok"


def test_skill_market_does_not_cache_an_empty_upstream_failure(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    from vera_agent.server.routes import skills as skills_routes

    def unavailable_upstream(*_args, **_kwargs):
        raise OSError("upstream unavailable")

    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", None)
    monkeypatch.setattr(
        skills_routes, "SKILL_SOURCES", {"sample": {"repo": "sample/skills", "root": "skills", "label": "Test source"}}
    )
    monkeypatch.setattr(skills_routes, "urlopen", unavailable_upstream)
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.get("/api/skills/market")

    assert response.status_code == 502
    assert response.json()["market"] == []
    cache_file = temp_git_repo / ".agents" / "registries" / "skills-market-cache.json"
    assert not cache_file.exists()


def test_skill_market_serves_saved_catalog_when_sources_are_unavailable(
    temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
):
    import time

    from vera_agent.server.routes import skills as skills_routes

    stale_item = {"market_id": "sample:review", "name": "review", "description": "Saved catalog item"}
    cache_file = temp_git_repo / ".agents" / "registries" / "skills-market-cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps({"version": 2, "fetched_at": time.time() - 25_000, "market": [stale_item]}), encoding="utf-8"
    )

    def unavailable_upstream(*_args, **_kwargs):
        raise OSError("upstream unavailable")

    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", None)
    monkeypatch.setattr(
        skills_routes, "SKILL_SOURCES", {"sample": {"repo": "sample/skills", "root": "skills", "label": "Test source"}}
    )
    monkeypatch.setattr(skills_routes, "urlopen", unavailable_upstream)
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.get("/api/skills/market")

    assert response.status_code == 200
    assert response.json()["market"] == [stale_item]


def test_module5_skills_ecosystem(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """Test Module 5: Skill Ecosystem management."""
    import time

    from vera_agent.server.routes import skills as skills_routes

    sample_market = [
        {
            "market_id": "sample:review",
            "name": "review",
            "source_id": "sample",
            "source_path": "skills/review",
            "description": "Code review guidance",
            "category": "Test source",
            "source": "https://github.com/sample/skills",
            "commit": "0123456789abcdef",
        }
    ]
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

    # 3. GET /api/skills lists the installed Skill
    installed_names = [s["name"] for s in client.get("/api/skills").json()["skills"]]
    assert "custom-tester" in installed_names

    # 4. DELETE /api/skills/{skill_name}
    res_del = client.delete("/api/skills/custom-tester")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "ok"

    names_after = [s["name"] for s in client.get("/api/skills").json()["skills"]]
    assert "custom-tester" not in names_after


def test_chat_rejects_unavailable_mcp_attachment(temp_git_repo: Path):
    agents_dir = temp_git_repo / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "mcp_servers.json").write_text(
        json.dumps(
            {
                "servers": [{"id": "sql-readonly", "enabled": False}],
            }
        ),
        encoding="utf-8",
    )
    client = TestClient(create_app(repo_root=temp_git_repo))

    response = client.post(
        "/api/chat/stream",
        json={
            "thread_id": "th_disabled_mcp_attachment",
            "content": "Please answer.",
            "attached_mcps": ["sql-readonly"],
        },
    )

    assert response.status_code == 409
    assert "Attached MCP server is disabled" in response.json()["error"]

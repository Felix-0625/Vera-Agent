import io
import json
from pathlib import Path

from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.tools.ops import read_file_op


def test_mcp_and_skill_settings_are_application_scoped(tmp_path: Path):
    app_root = tmp_path / "app"
    project_root = tmp_path / "project"
    app_root.mkdir()
    project_root.mkdir()
    app = create_app(repo_root=app_root)
    state = app.state.server_state
    state.init_workspace(project_root)

    state.save_json_config("mcp_servers.json", {"servers": [{"id": "global", "enabled": False}]})
    state.save_json_config("skills_config.json", {"disabled_skills": ["global-skill"]})

    assert json.loads((app_root / ".agents" / "mcp_servers.json").read_text(encoding="utf-8"))["servers"][0]["id"] == "global"
    assert json.loads((app_root / ".agents" / "skills_config.json").read_text(encoding="utf-8"))["disabled_skills"] == ["global-skill"]
    assert not (project_root / ".agents" / "mcp_servers.json").exists()
    assert not (project_root / ".agents" / "skills_config.json").exists()


def test_attached_skill_resources_can_be_read_without_opening_other_external_paths(tmp_path: Path):
    project = tmp_path / "project"
    skill = tmp_path / "app" / ".agents" / "skills" / "sample"
    project.mkdir()
    skill.mkdir(parents=True)
    (skill / "example.md").write_text("example content", encoding="utf-8")
    secret = tmp_path / "outside.txt"
    secret.write_text("not allowed", encoding="utf-8")

    allowed = read_file_op(skill / "example.md", base_dir=project, allowed_read_paths=[skill])
    denied = read_file_op(secret, base_dir=project, allowed_read_paths=[skill])

    assert allowed["returncode"] == 0
    assert "example content" in allowed["output"]
    assert denied["returncode"] == 1
    assert denied["exception_info"] == "AccessDenied"


def test_market_installs_registry_remote_disabled_by_default(tmp_path: Path, monkeypatch):
    import vera_agent.server.routes.mcp as mcp_routes

    app_root = tmp_path / "app"
    app_root.mkdir()
    client = TestClient(create_app(repo_root=app_root))
    payload = {
        "servers": [{
            "server": {
                "name": "com.example/remote",
                "title": "Example Remote",
                "version": "1.0.0",
                "repository": {"url": "https://github.com/example/remote"},
                "remotes": [{"type": "streamable-http", "url": "https://example.com/mcp"}],
                "packages": [],
            }
        }]
    }

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    monkeypatch.setattr(mcp_routes, "urlopen", lambda *_args, **_kwargs: FakeResponse(json.dumps(payload).encode()))
    response = client.post("/api/mcp/market/install", json={"registry_id": "com.example/remote"})

    assert response.status_code == 200
    server = response.json()["server"]
    assert server["type"] == "remote"
    assert server["url"] == "https://example.com/mcp"
    assert server["enabled"] is False
    saved = json.loads((app_root / ".agents" / "mcp_servers.json").read_text(encoding="utf-8"))
    assert saved["servers"] == [server]

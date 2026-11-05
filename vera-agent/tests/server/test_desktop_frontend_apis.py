"""Desktop frontend API contracts: project history, scheduled tasks, and global threads.

Validates:
1. Projects history: GET/DELETE /api/projects
2. Scheduled tasks: GET/POST/PATCH/DELETE /api/tasks/scheduled
3. Global threads: GET/POST /api/threads
4. Rules (AGENTS.md): GET/POST /api/settings/rules
5. File tree & preview: GET /api/files/tree, GET /api/files/content
6. Worktree diff & stage: GET /api/worktrees/diff, POST /api/worktrees/stage, POST /api/worktrees/discard
7. GitFlow branches: POST/DELETE /api/branches, checkout, merge
8. Model/MCP/Skill settings: PUT /api/mcp/servers/{id}, PATCH /api/settings/models/{id}, skills_config.json
"""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.server.routes.chat import _enabled_attached_skills


@pytest.fixture
def test_git_repo(tmp_path: Path):
    """Create a temporary initialized git repo with initial commit."""
    repo = tmp_path / "desktop_test_repo"
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

    run_git(["init"])
    run_git(["config", "user.name", "VeraTester"])
    run_git(["config", "user.email", "tester@vera.local"])

    # Create dummy initial file
    main_file = repo / "main.py"
    main_file.write_text("print('hello vera world')\n", encoding="utf-8")
    run_git(["add", "."])
    run_git(["commit", "-m", "Initial commit"])

    return repo


def test_projects_history_api(test_git_repo: Path):
    """Test GET /api/projects and DELETE /api/projects/{id}."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json().get("projects", [])
    assert len(projects) >= 1
    proj_id = projects[0]["id"]
    assert projects[0]["name"] == "desktop_test_repo"

    # Delete project
    del_res = client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    res_after = client.get("/api/projects")
    assert not any(p["id"] == proj_id for p in res_after.json()["projects"])


def test_scheduled_tasks_api(test_git_repo: Path):
    """Test full CRUD lifecycle for scheduled tasks."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # 1. Create task
    create_res = client.post(
        "/api/tasks/scheduled",
        json={
            "name": "Nightly Regression Suite",
            "run_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "prompt": "Run full regression test and report defects",
            "model_id": "test-model",
        },
    )
    assert create_res.status_code == 201
    task = create_res.json()
    task_id = task["id"]
    assert task["enabled"] is True

    # 2. List tasks
    list_res = client.get("/api/tasks/scheduled")
    assert list_res.status_code == 200
    assert any(t["id"] == task_id for t in list_res.json()["tasks"])

    # 3. Toggle task
    toggle_res = client.patch(f"/api/tasks/scheduled/{task_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    # 4. Trigger task
    run_res = client.post(f"/api/tasks/scheduled/{task_id}/run")
    assert run_res.status_code == 202
    assert run_res.json()["status"] == "started"

    # 5. Delete task
    del_res = client.delete(f"/api/tasks/scheduled/{task_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_threads_create_and_search(test_git_repo: Path):
    """Test standalone threads and search by message content."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # 1. Create standalone conversation
    create_res = client.post(
        "/api/threads",
        json={"title": "Refactor Payment Module", "role": "main"},
    )
    assert create_res.status_code == 200
    tid = create_res.json()["thread_id"]

    # 2. Add a user message directly to the persisted session
    session = app.state.server_state.get_or_create_session(tid)
    session.add_messages({"role": "user", "content": "How do we handle stripe webhooks?"})
    session.save(app.state.server_state.get_sessions_dir() / f"{tid}.json")

    # 3. Search threads
    search_res = client.get("/api/threads", params={"search": "stripe"})
    assert search_res.status_code == 200
    assert any(t["thread_id"] == tid for t in search_res.json()["threads"])


def test_rules_memory_api(test_git_repo: Path):
    """User rules and profile memories stay separate from project instructions."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # Context settings have safe defaults and AGENTS.md remains a separate file.
    get_res = client.get("/api/settings/rules")
    assert get_res.status_code == 200
    assert get_res.json()["user_rules"] == ""

    # Saving personal instructions does not create or overwrite project AGENTS.md.
    save_res = client.post(
        "/api/settings/rules",
        json={"content": "# Project Guidelines\n- Always write tests first.\n- Use conventional commits."},
    )
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "saved"
    assert not (test_git_repo / "AGENTS.md").exists()

    get_res_2 = client.get("/api/settings/context")
    assert get_res_2.status_code == 200
    assert "Always write tests first" in get_res_2.json()["user_rules"]
    assert get_res_2.json()["include_agents_md"] is True
    assert get_res_2.json()["memory_enabled"] is True

    created = client.post(
        "/api/settings/user-memories", json={"category": "preference", "content": "Prefers concise answers."}
    )
    assert created.status_code == 201
    memory_id = created.json()["memory"]["id"]
    assert client.get("/api/settings/user-memories").json()["memories"][0]["id"] == memory_id
    assert (
        client.patch(
            f"/api/settings/user-memories/{memory_id}",
            json={"category": "preference", "content": "Prefers detailed explanations."},
        ).status_code
        == 200
    )
    assert client.delete(f"/api/settings/user-memories/{memory_id}").status_code == 200


def test_file_tree_and_content_preview(test_git_repo: Path):
    """Test file tree exploration and preview with safety bounds."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # Create sub-directory and sample file
    sub_dir = test_git_repo / "src" / "utils"
    sub_dir.mkdir(parents=True, exist_ok=True)
    sample_code = sub_dir / "helper.py"
    sample_code.write_text("def helper():\n    return 42\n", encoding="utf-8")

    # 1. Get Tree
    tree_res = client.get("/api/files/tree")
    assert tree_res.status_code == 200
    tree_data = tree_res.json()
    assert tree_data["is_dir"] is True
    assert any(c["name"] == "src" for c in tree_data["children"])

    # 2. Get Content
    content_res = client.get("/api/files/content", params={"path": "src/utils/helper.py"})
    assert content_res.status_code == 200
    c_data = content_res.json()
    assert c_data["name"] == "helper.py"
    assert "return 42" in c_data["content"]
    assert c_data["lines"] == 2

    # 3. Path traversal attack rejection
    attack_res = client.get("/api/files/content", params={"path": "../../../etc/passwd"})
    assert attack_res.status_code in (403, 404)


def test_worktree_diff_and_staging(test_git_repo: Path):
    """Test diff inspection and file staging/discarding."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # Modify an existing file and create an untracked file
    main_file = test_git_repo / "main.py"
    main_file.write_text("print('modified vera world')\n", encoding="utf-8")
    untracked_file = test_git_repo / "new_feature.py"
    untracked_file.write_text("class Feature:\n    pass\n", encoding="utf-8")

    # 1. Diff endpoint
    diff_res = client.get("/api/worktrees/diff")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert any(f["file"] == "main.py" for f in diff_data["unstaged"])
    assert "new_feature.py" in diff_data["untracked"]
    assert "modified vera world" in diff_data["diff_text"]

    # 2. Stage main.py
    stage_res = client.post("/api/worktrees/stage", json={"files": ["main.py"]})
    assert stage_res.status_code == 200
    assert stage_res.json()["status"] == "staged"

    diff_res_after_stage = client.get("/api/worktrees/diff")
    assert any(f["file"] == "main.py" for f in diff_res_after_stage.json()["staged"])

    # 3. Discard
    discard_res = client.post("/api/worktrees/discard", json={"files": ["main.py"]})
    assert discard_res.status_code == 200
    assert discard_res.json()["status"] == "discarded"


def test_gitflow_branch_operations(test_git_repo: Path):
    """Test branch listing, creation, checkout, merge, and deletion."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)
    project_id = client.get("/api/projects").json()["projects"][0]["id"]

    # 1. List branches through the topology the UI renders
    list_res = client.get(f"/api/gitflow/topology?project_id={project_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()["branches"]) >= 1

    # 2. Create branch
    create_res = client.post("/api/branches", json={"branch_name": "feat/new-api", "project_id": project_id})
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "created"

    # 3. Checkout branch
    co_res = client.post("/api/branches/checkout", json={"branch_name": "feat/new-api", "project_id": project_id})
    assert co_res.status_code == 200
    assert co_res.json()["status"] == "checked_out"

    # Checkout back to default branch
    curr = list_res.json()["current_branch"]
    client.post("/api/branches/checkout", json={"branch_name": curr, "project_id": project_id})

    # 4. Delete branch
    del_res = client.delete(f"/api/branches/feat/new-api?project_id={project_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_gitflow_topology_uses_repository_commit_history(test_git_repo: Path):
    client = TestClient(create_app(repo_root=test_git_repo))

    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    response = client.get(f"/api/gitflow/topology?project_id={project_id}")

    assert response.status_code == 200
    topology = response.json()
    assert topology["repo_name"] == test_git_repo.name
    assert len(topology["commits"]) == 1
    assert topology["commits"][0]["subject"] == "Initial commit"
    assert topology["branches"][0]["head"] == topology["commits"][0]["hash"]


def test_mcp_and_skills_and_models_enhancements(test_git_repo: Path):
    """Test editing MCP server, toggling skill, and updating single model."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # Seed settings-owned entities before exercising update/toggle contracts.
    created_mcp = client.post(
        "/api/mcp/servers",
        json={"id": "mcp-server-dev", "name": "Dev MCP", "type": "local", "command": "python", "args": ["server.py"]},
    )
    assert created_mcp.status_code == 200
    installed_skill = client.post(
        "/api/skills/install",
        json={"name": "gitflow-spec", "description": "GitFlow test skill", "instructions": "# GitFlow\n"},
    )
    assert installed_skill.status_code == 200

    # 1. Edit MCP server preserving fields
    edit_mcp_res = client.put(
        "/api/mcp/servers/mcp-server-dev",
        json={"name": "Renamed Dev MCP", "command": "python3"},
    )
    assert edit_mcp_res.status_code == 200
    assert edit_mcp_res.json()["server"]["name"] == "Renamed Dev MCP"

    # 2. A Skill named in skills_config.json is hidden from chat and listed as disabled
    state = client.app.state.server_state
    state.save_json_config("skills_config.json", {"disabled_skills": ["gitflow-spec"]})
    listed_skill = next(
        skill for skill in client.get("/api/skills").json()["skills"] if skill["name"] == "gitflow-spec"
    )
    assert listed_skill["enabled"] is False
    assert _enabled_attached_skills(state, ["gitflow-spec"]) == []
    state.save_json_config("skills_config.json", {"disabled_skills": []})
    assert _enabled_attached_skills(state, ["gitflow-spec"]) == ["gitflow-spec"]

    # 3. Patch model config
    patch_model_res = client.patch(
        "/api/settings/models/model_deepseek",
        json={"temperature": 0.7, "max_tokens": 4096},
    )
    assert patch_model_res.status_code == 200
    assert patch_model_res.json()["model"]["temperature"] == 0.7
    assert patch_model_res.json()["model"]["max_tokens"] == 4096

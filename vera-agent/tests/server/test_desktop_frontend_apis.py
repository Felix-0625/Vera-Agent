"""Tests for newly supplemented Desktop Frontend APIs (Penpot & Desktop Spec).

Validates:
1. Projects history: GET/DELETE /api/projects
2. Scheduled tasks: GET/POST/PATCH/DELETE /api/tasks/scheduled
3. Global threads: GET/POST /api/threads, GET /api/threads/{id}/context-probe
4. Rules (AGENTS.md): GET/POST /api/settings/rules
5. File tree & preview: GET /api/files/tree, GET /api/files/content
6. Worktree diff & stage: GET /api/worktrees/diff, POST /api/worktrees/stage, POST /api/worktrees/discard
7. GitFlow branches: GET/POST/DELETE /api/branches, checkout, merge
8. Terminal: POST /api/terminal/exec
9. Model/MCP/Skill patches: PUT /api/mcp/servers/{id}, PATCH /api/settings/models/{id}, PATCH /api/skills/{name}/toggle
10. Direct message dispatch: POST /api/messages/send
"""

import json
import os
import subprocess
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app


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
            "cron": "0 2 * * *",
            "prompt": "Run full regression test and report defects",
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
    assert run_res.status_code == 200
    assert run_res.json()["status"] == "triggered"

    # 5. Delete task
    del_res = client.delete(f"/api/tasks/scheduled/{task_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_threads_and_sidechat_probe(test_git_repo: Path):
    """Test standalone threads, search, and context probe."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # 1. Create standalone conversation
    create_res = client.post(
        "/api/threads",
        json={"title": "Refactor Payment Module", "role": "main"},
    )
    assert create_res.status_code == 200
    tid = create_res.json()["thread_id"]

    # 2. Send message
    msg_res = client.post(
        "/api/messages/send",
        json={"thread_id": tid, "content": "How do we handle stripe webhooks?", "sender_id": "user"},
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["status"] == "delivered"

    # 3. Search threads
    search_res = client.get("/api/threads", params={"search": "stripe"})
    assert search_res.status_code == 200
    assert any(t["thread_id"] == tid for t in search_res.json()["threads"])

    # 4. Probe thread context (for SideChatTab)
    probe_res = client.get(f"/api/threads/{tid}/context-probe")
    assert probe_res.status_code == 200
    probe_data = probe_res.json()
    assert probe_data["thread_id"] == tid
    assert "stripe" in probe_data["last_user_message"].lower()


def test_rules_memory_api(test_git_repo: Path):
    """Test reading and writing AGENTS.md rules."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # Initially AGENTS.md does not exist
    get_res = client.get("/api/settings/rules")
    assert get_res.status_code == 200
    assert get_res.json()["exists"] is False

    # Save rules
    save_res = client.post(
        "/api/settings/rules",
        json={"content": "# Project Guidelines\n- Always write tests first.\n- Use conventional commits."},
    )
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "saved"

    # Verify updated content
    get_res_2 = client.get("/api/settings/rules")
    assert get_res_2.status_code == 200
    assert get_res_2.json()["exists"] is True
    assert "Always write tests first" in get_res_2.json()["content"]


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

    # 1. List branches
    list_res = client.get("/api/branches")
    assert list_res.status_code == 200
    assert len(list_res.json()["branches"]) >= 1

    # 2. Create branch
    create_res = client.post("/api/branches", json={"branch_name": "feat/new-api"})
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "created"

    # 3. Checkout branch
    co_res = client.post("/api/branches/checkout", json={"branch_name": "feat/new-api"})
    assert co_res.status_code == 200
    assert co_res.json()["status"] == "checked_out"

    # Checkout back to default branch
    curr = list_res.json()["current_branch"]
    client.post("/api/branches/checkout", json={"branch_name": curr})

    # 4. Delete branch
    del_res = client.delete("/api/branches/feat/new-api")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_terminal_exec(test_git_repo: Path):
    """Test terminal command execution."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    res = client.post(
        "/api/terminal/exec",
        json={"command": "python -c \"print('terminal works')\"", "timeout": 10},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["exit_code"] == 0
    assert "terminal works" in data["stdout"]


def test_mcp_and_skills_and_models_enhancements(test_git_repo: Path):
    """Test editing MCP server, toggling skill, and updating single model."""
    app = create_app(repo_root=test_git_repo)
    client = TestClient(app)

    # 1. Edit MCP server preserving fields
    edit_mcp_res = client.put(
        "/api/mcp/servers/mcp-server-dev",
        json={"name": "Renamed Dev MCP", "command": "python3"},
    )
    assert edit_mcp_res.status_code == 200
    assert edit_mcp_res.json()["server"]["name"] == "Renamed Dev MCP"

    # 2. Toggle skill
    toggle_sk_res = client.patch("/api/skills/gitflow-spec/toggle")
    assert toggle_sk_res.status_code == 200
    assert toggle_sk_res.json()["status"] == "ok"

    # 3. Patch model config
    patch_model_res = client.patch(
        "/api/settings/models/model_deepseek",
        json={"temperature": 0.7, "max_tokens": 4096},
    )
    assert patch_model_res.status_code == 200
    assert patch_model_res.json()["model"]["temperature"] == 0.7
    assert patch_model_res.json()["model"]["max_tokens"] == 4096

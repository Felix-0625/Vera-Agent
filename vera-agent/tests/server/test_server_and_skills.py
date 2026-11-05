"""Code intelligence tools, Skill discovery/activation, and core Starlette API routes."""

import os
import subprocess
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.tools.code_tools import check_syntax_op, find_references_op, symbol_search_op
from vera_agent.tools.skill_tools import SkillManager


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Create a temporary initialized git repo for server and tool tests."""
    repo = tmp_path / "server_test_repo"
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
    run_git(["config", "user.name", "ServerTester"])
    run_git(["config", "user.email", "server@test.local"])
    run_git(["config", "commit.gpgsign", "false"])

    sample_code = (
        "class PaymentProcessor:\n"
        "    '''Handles stripe charges.'''\n"
        "    def process_charge(self, amount: float) -> bool:\n"
        "        return True\n\n"
        "def helper_func():\n"
        "    pass\n"
    )
    (repo / "payment.py").write_text(sample_code, encoding="utf-8")
    run_git(["add", "."])
    run_git(["commit", "-m", "initial server repo commit"])

    return repo


def test_code_tools(temp_git_repo: Path):
    # 1. Syntax check
    valid, msg = check_syntax_op("def foo(): return 42\n")
    assert valid
    assert "OK" in msg

    invalid, err = check_syntax_op("def foo() return 42\n")
    assert not invalid
    assert "SyntaxError" in err

    # 2. Symbol search
    symbols = symbol_search_op(temp_git_repo, query="Payment")
    assert len(symbols) >= 1
    assert symbols[0]["name"] == "PaymentProcessor"
    assert symbols[0]["type"] == "class"

    funcs = symbol_search_op(temp_git_repo, query="helper_func", symbol_type="function")
    assert len(funcs) == 1
    assert funcs[0]["name"] == "helper_func"

    # 3. Find references
    refs = find_references_op(temp_git_repo, symbol_name="PaymentProcessor")
    assert len(refs) >= 1
    assert "class PaymentProcessor:" in refs[0]["content"]


def test_skill_manager(tmp_path: Path):
    skill_dir = tmp_path / ".agents" / "skills" / "docker_guide"
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        "name: docker-ops\n"
        "description: Guide for running docker commands in sandbox\n"
        "---\n\n"
        "Always use base64 encoding when writing scripts into docker containers.\n",
        encoding="utf-8",
    )

    manager = SkillManager(root_dirs=[tmp_path])
    skills = manager.list_skills()
    assert len(skills) == 1
    assert skills[0]["name"] == "docker-ops"
    assert "Guide for running docker" in skills[0]["description"]

    rendered = manager.render_skill_instruction("docker-ops")
    assert rendered is not None
    assert "<skill name='docker-ops'>" in rendered
    assert "base64 encoding" in rendered


def test_server_api_endpoints(temp_git_repo: Path):
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # 2. Create ProjectGroup
    res_group = client.post(
        "/api/groups",
        json={"group_id": "grp_auth", "branch_name": "feat/auth", "base_branch": "main"},
    )
    assert res_group.status_code == 200
    assert res_group.json()["group_id"] == "grp_auth"

    # 3. Checkpoint
    wt_path = res_group.json()["worktree_path"]
    (Path(wt_path) / "test_scratch.txt").write_text("wip", encoding="utf-8")
    res_cp = client.post(
        "/api/worktrees/checkpoint",
        json={"worktree_path": wt_path, "message": "api checkpoint test"},
    )
    assert res_cp.status_code == 200
    assert res_cp.json()["success"] is True

    # 4. Syntax validation endpoint
    res_syntax = client.post("/api/code/check-syntax", json={"code": "x = 1 + 2"})
    assert res_syntax.status_code == 200
    assert res_syntax.json()["valid"] is True

    # 5. Merge Review endpoint
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    res_merge = client.post(
        "/api/merge-review",
        json={"source_branch": "feat/auth", "target_branch": "main", "project_id": project_id},
    )
    assert res_merge.status_code == 200
    assert "can_merge" in res_merge.json()

"""Fixtures local to this regression suite."""

import os
import subprocess
from pathlib import Path

import pytest


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

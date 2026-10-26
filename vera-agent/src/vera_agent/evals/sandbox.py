"""Disposable workspaces for eval runs.

Each run gets ``<tmp>/vera-eval-*/`` with two directories:

- ``workspace/``: a new git repository holding the case fixture; the agent's only write boundary.
- ``config/``: the run's `projects_config_root`, so its `.agents/` (models, permissions, memories,
  traces, Skills) never touches the user's real configuration.

The workspace is created outside any user project, never inside one. Model settings are copied
from the user's config so the run uses a real model; nothing else is copied. Terminal commands
still run as the current OS user (VeraAgent is not an OS sandbox); `AutoApprovalPolicy` limits
them to each case's allowlist, and ``HOME``/``USERPROFILE``/``APPDATA`` point into the sandbox
for the acceptance script.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vera_agent.evals.cases import EvalCase
from vera_agent.evals.profile import AgentProfile

# Permission settings for every eval turn, independent of the user's saved permission mode:
# every terminal command and every non-file tool goes through the AutoApprovalPolicy.
EVAL_PERMISSIONS = {
    "default_mode": "manual",
    "approval_actions": ["terminal", "search", "mcp", "delegation"],
    "operation_scope": "project_only",
    "max_tool_attempts": 3,
}


@dataclass
class Sandbox:
    root: Path
    workspace: Path
    config_root: Path

    def isolated_env(self) -> dict[str, str]:
        home = self.root / "home"
        home.mkdir(exist_ok=True)
        overrides = {"HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home), "PYTHONIOENCODING": "utf-8"}
        return {**os.environ, **overrides}

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _git(workspace: Path, *args: str) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0"}
    subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True, env=env)


def create_sandbox(
    case: EvalCase,
    profile: AgentProfile,
    models_config: dict[str, Any],
    *,
    parent_dir: Path | None = None,
) -> Sandbox:
    """Create the run's workspace (fixture committed to git) and isolated config root."""
    root = Path(tempfile.mkdtemp(prefix=f"vera-eval-{case.case_id}-", dir=parent_dir))
    workspace, config_root = root / "workspace", root / "config"
    workspace.mkdir()
    (config_root / ".agents").mkdir(parents=True)
    for relative, content in case.fixture.items():
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _git(workspace, "init", "-b", "main")
    _git(workspace, "config", "user.name", "VeraEval")
    _git(workspace, "config", "user.email", "eval@vera.local")
    _git(workspace, "config", "commit.gpgsign", "false")
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "--allow-empty", "-m", "fixture")

    agents_dir = config_root / ".agents"
    (agents_dir / "models_config.json").write_text(json.dumps(models_config, ensure_ascii=False), encoding="utf-8")
    (agents_dir / "permissions_config.json").write_text(json.dumps(EVAL_PERMISSIONS), encoding="utf-8")
    # The eval measures the profile, not the user's saved rules; AGENTS.md comes from the fixture.
    context = {"user_rules": "", "include_agents_md": True, "memory_enabled": bool(profile.memories)}
    (agents_dir / "user_context.json").write_text(json.dumps(context), encoding="utf-8")
    (agents_dir / "telemetry_config.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")
    for name, text in profile.skills.items():
        skill_dir = config_root / ".agents" / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    return Sandbox(root=root, workspace=workspace, config_root=config_root)


def run_acceptance(sandbox: Sandbox, case: EvalCase) -> dict[str, Any]:
    """Run the case's acceptance script in the workspace; exit code 0 means pass."""
    from vera_agent.environments.local import _find_windows_bash

    command = (
        [_find_windows_bash(), "--noprofile", "--norc", "-c", case.accept]
        if os.name == "nt"
        else ["bash", "-c", case.accept]
    )
    try:
        completed = subprocess.run(
            command,
            cwd=sandbox.workspace,
            env=sandbox.isolated_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=case.timeout,
        )
        output = (completed.stdout + completed.stderr)[-4000:]
        return {"passed": completed.returncode == 0, "returncode": completed.returncode, "output": output}
    except subprocess.TimeoutExpired:
        return {"passed": False, "returncode": -1, "output": f"Acceptance timed out after {case.timeout}s"}

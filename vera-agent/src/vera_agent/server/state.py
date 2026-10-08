"""Shared ServerState and lifecycle management for the VeraAgent ASGI application.

Maintains repository context, session registry, WorktreeManager, GitFlowGraph,
SessionRouter, RegistryManager, and configuration utilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from vera_agent.session.graph import GitFlowGraph
from vera_agent.session.pipeline import HandoffPipeline
from vera_agent.session.router import SessionRouter
from vera_agent.session.registry import RegistryManager
from vera_agent.session.thread import ThreadSession
from vera_agent.session.worktree import WorktreeManager
from vera_agent.tools.skill_tools import SkillManager

logger = logging.getLogger("vera_server.state")


def get_git_branch(repo_path: Path) -> str:
    """Safely get current git branch name."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "main"


class ServerState:
    """Encapsulates all runtime server dependencies and persistent configuration helpers."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        graph: GitFlowGraph | None = None,
    ):
        self.root_path: Path = Path.cwd()
        self.wt_manager: WorktreeManager | None = None
        self.graph: GitFlowGraph | None = None
        self.router: SessionRouter | None = None
        self.pipeline: HandoffPipeline | None = None
        self.skill_mgr: SkillManager | None = None
        self.registry_mgr: RegistryManager | None = None

        self.sessions: dict[str, ThreadSession] = {}
        self.pending_approvals: dict[str, asyncio.Future[str]] = {}
        self.interruption_flags: dict[str, bool] = {}

        self.init_workspace(Path(repo_root or Path.cwd()))
        if graph is not None:
            self.graph = graph
            self.router = SessionRouter(graph=graph)
            self.pipeline = HandoffPipeline(graph=graph)

    def load_json_config(self, file_name: str, default_data: Any) -> Any:
        cfg_file = self.root_path / ".agents" / file_name
        if cfg_file.exists():
            try:
                return json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default_data

    def save_json_config(self, file_name: str, data: Any) -> None:
        cfg_file = self.root_path / ".agents" / file_name
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def init_workspace(self, target_root: Path) -> None:
        resolved_root = target_root.resolve()
        wt = WorktreeManager(repo_root=resolved_root)
        active_g = GitFlowGraph(repo_root=resolved_root, worktree_manager=wt)
        self.root_path = resolved_root
        self.wt_manager = wt
        self.graph = active_g
        self.router = SessionRouter(graph=active_g)
        self.pipeline = HandoffPipeline(graph=active_g)
        self.skill_mgr = SkillManager(root_dirs=[resolved_root])
        self.registry_mgr = RegistryManager(resolved_root)

        # Update projects history
        proj_hist = self.load_json_config("projects_history.json", {"projects": []})
        projects = proj_hist.get("projects", [])
        path_str = str(resolved_root)
        existing = next((p for p in projects if p.get("path") == path_str), None)
        if existing:
            existing["last_opened_at"] = time.time()
            existing["is_git"] = (resolved_root / ".git").exists()
            existing["active_branch"] = get_git_branch(resolved_root)
        else:
            projects.append({
                "id": f"proj_{uuid.uuid4().hex[:8]}",
                "name": resolved_root.name,
                "path": path_str,
                "is_git": (resolved_root / ".git").exists(),
                "active_branch": get_git_branch(resolved_root),
                "last_opened_at": time.time(),
            })
        proj_hist["projects"] = projects
        self.save_json_config("projects_history.json", proj_hist)

    def get_sessions_dir(self) -> Path:
        d = self.root_path / ".agents" / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_or_create_session(
        self,
        thread_id: str,
        group_id: str | None = None,
        role: str = "main",
        title: str = "",
    ) -> ThreadSession:
        if thread_id in self.sessions:
            s = self.sessions[thread_id]
            if role and role != s.role:
                s.role = role
            if group_id and group_id != s.group_id:
                s.group_id = group_id
            return s

        # Try to restore from disk snapshot
        s_file = self.get_sessions_dir() / f"{thread_id}.json"
        if s_file.exists():
            try:
                s = ThreadSession.load(s_file)
                self.sessions[thread_id] = s
                return s
            except Exception:
                pass

        # Create new
        s = ThreadSession(
            thread_id=thread_id,
            group_id=group_id,
            role=role,
            title=title or f"Thread {thread_id[:8]}",
        )
        self.sessions[thread_id] = s
        if self.graph:
            self.graph.register_session(thread_id, role=role, group_id=group_id)
        return s

    def run_git(self, args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        work_dir = cwd or self.root_path
        try:
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            res = subprocess.run(
                ["git", *args],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
                env=env,
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return -1, "", str(e)

"""Process-wide runtime state shared by all API routes (`ServerState`).

Two roots matter:

- `projects_config_root`: application data root (the `repo_root` passed to
  `create_app`, default: process cwd). Application-scoped JSON configs
  (projects history, models, permissions, MCP servers, Skills) live in
  `<projects_config_root>/.agents/`.
- `root_path`: the currently bound project. Other configs and default
  sessions live in `<root_path>/.agents/`; project sessions live in
  `<project>/.agents/sessions/<thread_id>.json`.

Also holds in-memory objects that are not persisted: active `ThreadSession`
objects, pending tool approvals, and chat interrupt/pause flags.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from vera_agent.session.graph import GitFlowGraph
from vera_agent.session.pipeline import HandoffPipeline
from vera_agent.session.registry import RegistryManager
from vera_agent.session.router import SessionRouter
from vera_agent.session.thread import ThreadSession
from vera_agent.session.worktree import WorktreeManager
from vera_agent.tools.skill_tools import SkillManager

logger = logging.getLogger("vera_server.state")

# Settings shared by every project; stored under `<projects_config_root>/.agents/`.
APPLICATION_CONFIGS = frozenset(
    {
        "projects_history.json",
        "models_config.json",
        "permissions_config.json",
        "mcp_servers.json",
        "skills_config.json",
    }
)


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
        self.projects_config_root: Path = Path(repo_root or Path.cwd()).resolve()
        self.wt_manager: WorktreeManager | None = None
        self.graph: GitFlowGraph | None = None
        self.router: SessionRouter | None = None
        self.pipeline: HandoffPipeline | None = None
        self.skill_mgr: SkillManager | None = None
        self.registry_mgr: RegistryManager | None = None

        self.sessions: dict[str, ThreadSession] = {}
        self.pending_approvals: dict[str, asyncio.Future[str]] = {}
        self.interruption_flags: dict[str, bool] = {}
        self.active_chat_message_ids: dict[str, str] = {}
        self.pending_chat_interruptions: dict[str, float] = {}
        self.paused_chat_threads: set[str] = set()
        self.chat_pause_events: dict[str, threading.Event] = {}
        self.active_chat_threads: set[str] = set()

        self.init_workspace(Path(repo_root or Path.cwd()), record_history=repo_root is not None)
        if graph is not None:
            self.graph = graph
            self.router = SessionRouter(graph=graph)
            self.pipeline = HandoffPipeline(graph=graph)

    def load_json_config(self, file_name: str, default_data: Any) -> Any:
        config_root = self.projects_config_root if file_name in APPLICATION_CONFIGS else self.root_path
        cfg_file = config_root / ".agents" / file_name
        if cfg_file.exists():
            try:
                return json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        # Routes often mutate a loaded config before saving it. Never hand out a
        # shared module-level default object: one request could contaminate the
        # next app instance or test.
        return copy.deepcopy(default_data)

    def save_json_config(self, file_name: str, data: Any) -> None:
        config_root = self.projects_config_root if file_name in APPLICATION_CONFIGS else self.root_path
        cfg_file = config_root / ".agents" / file_name
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def init_workspace(
        self,
        target_root: Path,
        project_id: str | None = None,
        project_name: str | None = None,
        folders: list[str] | None = None,
        record_history: bool = True,
    ) -> None:
        resolved_root = target_root.resolve()
        wt = WorktreeManager(repo_root=resolved_root)
        active_g = GitFlowGraph(repo_root=resolved_root, worktree_manager=wt)
        self.root_path = resolved_root
        self.wt_manager = wt
        self.graph = active_g
        self.router = SessionRouter(graph=active_g)
        self.pipeline = HandoffPipeline(graph=active_g)
        skill_roots = [resolved_root]
        if self.projects_config_root not in skill_roots:
            skill_roots.append(self.projects_config_root)
        self.skill_mgr = SkillManager(root_dirs=skill_roots)
        self.registry_mgr = RegistryManager(resolved_root)

        if not record_history:
            return
        # Update projects history
        proj_hist = self.load_json_config("projects_history.json", {"projects": []})
        projects = proj_hist.get("projects", [])
        path_str = str(resolved_root)
        existing = next(
            (p for p in projects if (project_id and p.get("id") == project_id) or p.get("path") == path_str), None
        )
        if existing:
            existing["path"] = path_str
            if project_name:
                existing["name"] = project_name
            existing["last_opened_at"] = time.time()
            existing["is_git"] = (resolved_root / ".git").exists()
            existing["active_branch"] = get_git_branch(resolved_root)
            existing["folders"] = folders or existing.get("folders") or [path_str]
        else:
            projects.append(
                {
                    "id": project_id or f"proj_{uuid.uuid4().hex[:8]}",
                    "name": project_name or resolved_root.name,
                    "path": path_str,
                    "folders": folders or [path_str],
                    "is_git": (resolved_root / ".git").exists(),
                    "active_branch": get_git_branch(resolved_root),
                    "last_opened_at": time.time(),
                }
            )
        proj_hist["projects"] = projects
        self.save_json_config("projects_history.json", proj_hist)

    def get_sessions_dir(self) -> Path:
        d = self.root_path / ".agents" / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_project_root(self, project_id: str | None = None) -> Path:
        if not project_id:
            return self.root_path
        projects = self.load_json_config("projects_history.json", {"projects": []}).get("projects", [])
        project = next((item for item in projects if item.get("id") == project_id), None)
        if not project or not project.get("path"):
            raise ValueError(f"Project '{project_id}' not found")
        project_root = Path(project["path"]).resolve()
        if not project_root.is_dir():
            raise ValueError(f"Project directory does not exist: {project_root}")
        return project_root

    def get_session_file(self, session: ThreadSession) -> Path:
        project_root = session.metadata.get("project_root")
        session_dir = Path(project_root) / ".agents" / "sessions" if project_root else self.get_sessions_dir()
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"{session.thread_id}.json"

    def infer_legacy_session_project_id(
        self,
        session_file: Path,
        session: ThreadSession,
        fallback_project_id: str | None = None,
    ) -> str | None:
        """Infer project ownership only for session files written before project_id was stored.

        A persisted null is an explicit unbound conversation. Treating it as legacy data
        would silently bind it to whichever project happens to own the containing folder.
        """
        if getattr(session, "_project_id_is_explicit", True):
            return session.project_id

        project = next(
            (
                item
                for item in self.load_json_config("projects_history.json", {"projects": []}).get("projects", [])
                if item.get("path") and Path(item["path"]).resolve() == session_file.parents[2].resolve()
            ),
            None,
        )
        return project.get("id") if project else fallback_project_id

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
        session_files = [self.get_sessions_dir() / f"{thread_id}.json"]
        for project in self.load_json_config("projects_history.json", {"projects": []}).get("projects", []):
            project_path = project.get("path")
            if project_path:
                candidate = Path(project_path) / ".agents" / "sessions" / f"{thread_id}.json"
                if candidate not in session_files:
                    session_files.append(candidate)
        for s_file in session_files:
            if s_file.exists():
                try:
                    s = ThreadSession.load(s_file)
                    s.project_id = self.infer_legacy_session_project_id(s_file, s)
                    s.metadata.setdefault("project_root", str(s_file.parents[2]))
                    self.sessions[thread_id] = s
                    return s
                except Exception:
                    continue

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

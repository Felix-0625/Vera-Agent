"""Minimalist Git Worktree and branch lifecycle manager.

Adheres to Pi-agent minimalism and Git-native porcelain standards:
- WorktreeManager: Safe creation, removal, checkpointing, and in-memory merge checking.
- Uses standard git porcelain interfaces for zero-dependency reliability.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WorktreeManager:
    """Manages Git Worktrees for concurrent agent task isolation."""

    def __init__(self, repo_root: Path | str, worktrees_dir: Path | str | None = None):
        self.repo_root = Path(repo_root).resolve()
        if worktrees_dir:
            self.worktrees_dir = Path(worktrees_dir).resolve()
        else:
            self.worktrees_dir = self.repo_root / ".agents" / "worktrees"
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    def _run_git(
        self,
        args: list[str],
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a git command safely with UTF-8 encoding."""
        target_cwd = str(cwd or self.repo_root)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            return subprocess.run(
                ["git", *args],
                cwd=target_cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=check,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            logger.warning("Git command failed: git %s in %s: %s", " ".join(args), target_cwd, e.stderr)
            raise

    def list_worktrees(self) -> list[dict[str, Any]]:
        """List all registered worktrees using git porcelain format."""
        proc = self._run_git(["worktree", "list", "--porcelain"])
        worktrees = []
        current: dict[str, Any] = {}

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                if current and "path" in current:
                    worktrees.append(current)
                    current = {}
                continue
            if line.startswith("worktree "):
                current["path"] = str(Path(line[len("worktree ") :]).resolve())
            elif line.startswith("HEAD "):
                current["commit"] = line[len("HEAD ") :]
            elif line.startswith("branch "):
                current["branch"] = line[len("branch ") :].replace("refs/heads/", "")
            elif line == "bare":
                current["bare"] = True

        if current and "path" in current:
            worktrees.append(current)

        return worktrees

    def get_worktree_for_branch(self, branch: str) -> Path | None:
        """Find the worktree path corresponding to a branch if checked out."""
        for wt in self.list_worktrees():
            if wt.get("branch") == branch:
                return Path(wt["path"])
        return None

    def create_worktree(
        self,
        branch: str,
        base_branch: str = "main",
        worktree_name: str | None = None,
    ) -> Path:
        """Create a new worktree checked out to branch.

        If branch does not exist, it will be branched from base_branch.
        """
        existing = self.get_worktree_for_branch(branch)
        if existing and existing.exists():
            return existing

        name = worktree_name or branch.replace("/", "_").replace("\\", "_")
        target_path = (self.worktrees_dir / name).resolve()

        if target_path.exists():
            # If directory exists without active worktree registration, prune or remove
            self._run_git(["worktree", "prune"], check=False)
            if target_path.exists() and not (target_path / ".git").exists():
                import shutil

                shutil.rmtree(target_path, ignore_errors=True)

        # Check if branch exists
        branch_check = self._run_git(["rev-parse", "--verify", branch], check=False)
        if branch_check.returncode == 0:
            # Branch exists, check it out in new worktree
            self._run_git(["worktree", "add", str(target_path), branch])
        else:
            # Create new branch from base_branch
            self._run_git(["worktree", "add", "-b", branch, str(target_path), base_branch])

        return target_path

    def remove_worktree(self, branch: str, force: bool = False) -> bool:
        """Remove a worktree associated with a branch."""
        wt_path = self.get_worktree_for_branch(branch)
        if not wt_path:
            return False

        args = ["worktree", "remove", str(wt_path)]
        if force:
            args.append("--force")

        try:
            self._run_git(args)
            self._run_git(["worktree", "prune"], check=False)
            return True
        except subprocess.CalledProcessError:
            if force and wt_path.exists():
                import shutil

                shutil.rmtree(wt_path, ignore_errors=True)
                self._run_git(["worktree", "prune"], check=False)
                return True
            return False

    def get_worktree_status(self, worktree_path: Path | str) -> dict[str, Any]:
        """Check if worktree is dirty and list modified files."""
        path = Path(worktree_path).resolve()
        proc = self._run_git(["status", "--porcelain"], cwd=path)
        dirty_files = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line:
                # Format: XY filename
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    dirty_files.append({"status": parts[0], "file": parts[1]})

        commit_proc = self._run_git(["rev-parse", "--short", "HEAD"], cwd=path, check=False)
        head_commit = commit_proc.stdout.strip() if commit_proc.returncode == 0 else ""

        return {
            "is_dirty": len(dirty_files) > 0,
            "dirty_files": dirty_files,
            "head_commit": head_commit,
            "path": str(path),
        }

    def create_checkpoint(self, worktree_path: Path | str, message: str) -> str:
        """Aider-style ephemeral checkpoint commit.

        Stages uncommitted changes and creates an atomic checkpoint commit
        allowing easy rollback and multi-agent handover without polluting base branches.
        """
        path = Path(worktree_path).resolve()
        status = self.get_worktree_status(path)
        if not status["is_dirty"]:
            return status["head_commit"]

        commit_msg = f"[checkpoint] {message.strip()}"
        self._run_git(["add", "-A"], cwd=path)
        self._run_git(["commit", "-m", commit_msg, "--no-verify"], cwd=path)

        commit_proc = self._run_git(["rev-parse", "--short", "HEAD"], cwd=path)
        return commit_proc.stdout.strip()

    def reset_worktree(self, worktree_path: Path | str, hard: bool = True) -> bool:
        """Reset dirty state in a worktree without touching other worktrees."""
        path = Path(worktree_path).resolve()
        try:
            if hard:
                self._run_git(["checkout", "."], cwd=path)
                self._run_git(["clean", "-fd"], cwd=path)
            else:
                self._run_git(["checkout", "."], cwd=path)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_diff(
        self,
        worktree_path: Path | str,
        base_branch: str = "main",
    ) -> str:
        """Get git diff of the worktree against base_branch."""
        path = Path(worktree_path).resolve()
        proc = self._run_git(["diff", f"{base_branch}...HEAD"], cwd=path, check=False)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        # Fallback to direct diff
        proc_direct = self._run_git(["diff", base_branch], cwd=path, check=False)
        return proc_direct.stdout if proc_direct.returncode == 0 else ""

    def try_merge(
        self,
        source_branch: str,
        target_branch: str,
    ) -> tuple[bool, list[str], str]:
        """Perform a safe in-memory 3-way merge inspection using git merge-tree.

        Returns:
            (can_merge, conflict_files, diff_or_conflict_summary)
        """
        proc = self._run_git(
            ["merge-tree", "--write-tree", target_branch, source_branch],
            check=False,
        )
        output = proc.stdout + proc.stderr
        conflict_files = []

        if proc.returncode == 0:
            # Successful in-memory merge
            return True, [], output.strip()

        # Parse conflicts
        for line in output.splitlines():
            line = line.strip()
            if "CONFLICT" in line:
                conflict_files.append(line)

        return False, conflict_files, output.strip()

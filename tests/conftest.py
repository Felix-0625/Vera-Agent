"""Shared paths for repository-level tests.

Run from the repository root with the backend environment::

    vera-agent\\.venv\\Scripts\\python.exe -m pytest tests
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def tracked_files() -> list[str]:
    """Paths tracked by Git plus new files that are not ignored (what a commit would contain)."""
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return sorted({line for line in output.splitlines() if line and (REPO_ROOT / line).exists()})

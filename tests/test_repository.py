"""Repository hygiene for an open-source checkout: no secrets, residue, or unreproducible installs."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".yml", ".yaml", ".toml", ".ps1", ".html", ".css"}


def test_lockfiles_are_committed(tracked_files: list[str]):
    assert "vera-agent/uv.lock" in tracked_files, "uv.lock must be tracked: install docs and CI use `uv sync --locked`"
    assert "frontend/package-lock.json" in tracked_files


def test_files_opened_by_backend_tests_are_tracked(tracked_files: list[str]):
    """Fixtures read by tests must not be hidden by ignore rules (e.g. `*.traj.json`)."""
    fixtures = sorted((REPO_ROOT / "vera-agent" / "tests" / "test_data").glob("*.json"))
    missing = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in fixtures
        if p.relative_to(REPO_ROOT).as_posix() not in tracked_files
    ]
    assert not missing, f"Test fixtures excluded from Git: {missing}"


def test_no_local_state_or_build_output_is_tracked(tracked_files: list[str]):
    forbidden = re.compile(
        r"(^|/)(\.agents|node_modules|dist|build|__pycache__|\.venv|scratch)/|\.env$|\.traj\.json$|\.sqlite$"
    )
    fixtures = "vera-agent/tests/test_data/"
    assert not [path for path in tracked_files if forbidden.search(path) and not path.startswith(fixtures)]


def test_no_secrets_in_tracked_text(tracked_files: list[str]):
    pattern = re.compile(
        r"(sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
    )
    hits = []
    for relative in tracked_files:
        path = REPO_ROOT / relative
        if path.suffix in TEXT_SUFFIXES and relative != "frontend/package-lock.json":
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(relative)
    assert not hits, f"Possible secrets in: {hits}"


def test_not_set_up_for_npm_publishing(tracked_files: list[str]):
    """The project is distributed as GitHub source only; npm is just the frontend build tool."""
    assert "package.json" not in tracked_files, "unexpected root package.json (removed npm installer)"
    assert not [path for path in tracked_files if path.startswith("installer/") or path.endswith(".npmignore")]
    frontend = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert frontend["private"] is True
    assert not {"bin", "publishConfig", "files"} & frontend.keys()


def test_source_comments_are_english(tracked_files: list[str]):
    """Comments and docstrings are English; Chinese UI strings and prompts are allowed."""
    cjk = re.compile(r"[一-鿿]")
    offenders = []
    for relative in tracked_files:
        if not relative.endswith((".py", ".ts", ".tsx")) or "/tests/" in relative or relative.startswith("tests/"):
            continue
        for number, line in enumerate((REPO_ROOT / relative).read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            comment = None
            if relative.endswith(".py") and stripped.startswith("#"):
                comment = stripped
            elif relative.endswith((".ts", ".tsx")) and (stripped.startswith(("//", "/*", "* ")) or stripped == "*"):
                comment = stripped
            if comment and cjk.search(comment):
                offenders.append(f"{relative}:{number}")
    assert not offenders, "Non-English comments:\n" + "\n".join(offenders)


def test_repository_stores_text_with_lf_line_endings():
    """Checks the index, not the working tree: Windows checkouts may convert to CRLF locally."""
    output = subprocess.run(
        ["git", "ls-files", "--eol"], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    offenders = [line.split("\t")[-1] for line in output.splitlines() if line.startswith(("i/crlf", "i/mixed"))]
    assert not offenders, f"CRLF stored in Git (run `git add --renormalize .`): {offenders[:20]}"


def test_gitattributes_normalizes_line_endings():
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in attributes

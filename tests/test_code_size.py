"""Keep source files and functions small enough to review; known large files may only shrink."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_LINES = 450
MAX_FUNCTION_LINES = 120

# Existing files above the limit, with their current size as a ceiling. Lower a ceiling when a
# file shrinks; remove the entry once the file is under MAX_FILE_LINES. Do not raise ceilings.
FILE_CEILINGS = {
    "vera-agent/src/vera_agent/server/routes/threads.py": 495,
}

# Existing long functions (name -> ceiling); same rule as FILE_CEILINGS.
FUNCTION_CEILINGS = {
    "models/litellm_model.py:query_stream": 130,
    "models/utils/actions_toolcall.py:parse_toolcall_actions": 122,
    "server/chat/request.py:parse_chat_request": 149,
    "server/routes/analytics.py:get_analytics_dashboard": 170,
    "server/routes/mcp.py:install_mcp_market": 165,
    "server/routes/runs.py:update_group_run": 150,
    "server/routes/skills.py:get_skills_market": 163,
    "server/routes/skills.py:fetch_market": 137,
    "server/routes/tasks.py:_execute_task": 129,
    "session/context_management.py:compact_session": 169,
}

SOURCE_GLOBS = ("vera-agent/src/vera_agent/**/*.py", "frontend/src/**/*.ts", "frontend/src/**/*.tsx")
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".ps1", ".bat"}


def test_all_own_code_files_have_a_hard_upper_limit():
    """Include tests, styles, scripts and website code; exclude generated locks and upstream vendor assets."""
    names = (
        subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=REPO_ROOT)
        .decode()
        .split("\0")
    )
    problems = []
    for name in set(names):
        path = REPO_ROOT / name
        if not path.is_file() or path.suffix not in CODE_SUFFIXES or "/vendor/" in name:
            continue
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > 1000:
            problems.append(f"{name}: {count} lines")
    assert not problems, "Split self-owned files exceeding 1000 lines:\n" + "\n".join(sorted(problems))


def _sources() -> list[Path]:
    files = {path for pattern in SOURCE_GLOBS for path in REPO_ROOT.glob(pattern)}
    return sorted(path for path in files if ".test." not in path.name and "__pycache__" not in path.parts)


def test_source_files_stay_small():
    problems = []
    for path in _sources():
        relative = path.relative_to(REPO_ROOT).as_posix()
        lines = len(path.read_text(encoding="utf-8").splitlines())
        limit = FILE_CEILINGS.get(relative, MAX_FILE_LINES)
        if lines > limit:
            problems.append(f"{relative}: {lines} lines (limit {limit})")
    assert not problems, "Split these files instead of growing them:\n" + "\n".join(problems)


def test_python_functions_stay_small():
    package = REPO_ROOT / "vera-agent" / "src" / "vera_agent"
    problems = []
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(package).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = node.end_lineno - node.lineno + 1
                key = f"{relative}:{node.name}"
                limit = FUNCTION_CEILINGS.get(key, MAX_FUNCTION_LINES)
                if length > limit:
                    problems.append(f"{key}: {length} lines (limit {limit})")
    assert not problems, "Extract helpers from these functions:\n" + "\n".join(problems)


def test_ceilings_are_not_stale():
    """A ceiling far above the current size hides growth; tighten it after refactors."""
    stale = []
    for relative, limit in FILE_CEILINGS.items():
        lines = len((REPO_ROOT / relative).read_text(encoding="utf-8").splitlines())
        if lines <= MAX_FILE_LINES or limit - lines > 50:
            stale.append(f"{relative}: {lines} lines, ceiling {limit}")
    assert not stale, "Update FILE_CEILINGS:\n" + "\n".join(stale)

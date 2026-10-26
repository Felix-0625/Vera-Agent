"""Eval case files and their splits.

A case is one YAML file::

    id: fix-off-by-one
    task: "The test in test_window.py fails. Fix the bug in window.py."
    split: train            # train | holdout | guard
    tags: [fix, python]
    fixture:                # files written into a fresh git repository before the run
      window.py: |
        def last(items, n): ...
    accept: python -m pytest -q   # acceptance script; exit code 0 means pass
    allowed_commands: ["python -m pytest*"]   # terminal commands the auto-approval may run
    max_tool_calls: 12      # optional per-case tool budget
    timeout: 120            # optional acceptance timeout in seconds

``train`` cases may be shown to the Critic, ``holdout`` cases decide whether a proposal helps and
are reported to proposals only as pass counts, and ``guard`` cases cover core abilities that may
never regress. The optimizer never writes case files (`evolution/` only reads them).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

SPLITS = ("train", "holdout", "guard")
BUILTIN_CASES_DIR = Path(__file__).parent / "cases"
_CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


class EvalCaseError(ValueError):
    """A case file is missing a field or has an invalid value."""


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    task: str
    split: str
    accept: str
    fixture: dict[str, str] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    allowed_commands: tuple[str, ...] = ()
    max_tool_calls: int = 15
    timeout: int = 120
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "task": self.task,
            "split": self.split,
            "tags": list(self.tags),
            "source_path": self.source_path,
        }


def _safe_fixture_path(name: str) -> str:
    path = PurePosixPath(name.replace("\\", "/"))
    # Reject rooted ("/x", "\x") and drive ("C:x") paths on every OS, not only the host's notion of absolute.
    if not name.strip() or path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", name):
        raise EvalCaseError(f"Fixture path must stay inside the sandbox: {name!r}")
    if path.parts and path.parts[0] == ".agents":
        raise EvalCaseError("Fixture files may not write the sandbox's .agents config directory.")
    return path.as_posix()


def parse_case(data: Any, source_path: str = "") -> EvalCase:
    if not isinstance(data, dict):
        raise EvalCaseError(f"{source_path}: a case must be a mapping")
    case_id = str(data.get("id") or "")
    if not _CASE_ID.fullmatch(case_id):
        raise EvalCaseError(f"{source_path}: id must be lowercase letters, digits and dashes")
    split = str(data.get("split") or "")
    if split not in SPLITS:
        raise EvalCaseError(f"{source_path}: split must be one of {', '.join(SPLITS)}")
    task, accept = str(data.get("task") or "").strip(), str(data.get("accept") or "").strip()
    if not task or not accept:
        raise EvalCaseError(f"{source_path}: task and accept are required")
    fixture = data.get("fixture") or {}
    if not isinstance(fixture, dict):
        raise EvalCaseError(f"{source_path}: fixture must map file paths to contents")
    try:
        max_tool_calls = max(1, min(int(data.get("max_tool_calls", 15)), 60))
        timeout = max(5, min(int(data.get("timeout", 120)), 900))
    except (TypeError, ValueError) as error:
        raise EvalCaseError(f"{source_path}: max_tool_calls and timeout must be integers") from error
    return EvalCase(
        case_id=case_id,
        task=task,
        split=split,
        accept=accept,
        fixture={_safe_fixture_path(str(name)): str(content) for name, content in fixture.items()},
        tags=tuple(str(tag) for tag in data.get("tags") or ()),
        allowed_commands=tuple(str(command) for command in data.get("allowed_commands") or ()),
        max_tool_calls=max_tool_calls,
        timeout=timeout,
        source_path=source_path,
    )


def load_cases(directories: list[Path] | None = None, splits: list[str] | None = None) -> list[EvalCase]:
    """Load every ``*.yaml`` case below ``directories`` (default: built-in cases), sorted by id."""
    cases: dict[str, EvalCase] = {}
    for directory in directories or [BUILTIN_CASES_DIR]:
        for path in sorted(Path(directory).rglob("*.yaml")):
            case = parse_case(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
            if case.case_id in cases:
                raise EvalCaseError(f"Duplicate case id {case.case_id!r} in {path}")
            cases[case.case_id] = case
    selected = [case for case in cases.values() if not splits or case.split in splits]
    return sorted(selected, key=lambda case: case.case_id)

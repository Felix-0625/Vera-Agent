"""Eval case drafts from low-score traces: how the eval set grows with use.

Each low-score desktop trace gets one draft at `<config root>/.agents/evals/drafts/<trace_id>.yaml`.
A draft holds the user's request and the files the agent touched, with ``accept`` left as a
``TODO`` so it cannot pass validation until the user writes a real acceptance check. Saving a
completed draft moves it to `.agents/evals/cases/`, where `vera-eval` picks it up; new cases go
to ``train`` by default because the Critic may look at them. Drafts never contain tool output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from vera_agent.evals.cases import EvalCaseError, parse_case
from vera_agent.utils.redact import redact_secrets

_TRACE_ID = re.compile(r"^trc_[a-f0-9]{16}$")


def _drafts_dir(config_root: Path | str) -> Path:
    return Path(config_root) / ".agents" / "evals" / "drafts"


def touched_paths(trace: dict[str, Any]) -> list[str]:
    paths = []
    for span in trace.get("spans", []):
        path = (span.get("input") or {}).get("path") if isinstance(span.get("input"), dict) else None
        if span.get("kind") == "tool" and isinstance(path, str) and path:
            paths.append(path)
    return list(dict.fromkeys(paths))[:20]


def draft_from_trace(config_root: Path | str, trace: dict[str, Any]) -> Path | None:
    """Write a draft for ``trace`` unless one exists; returns its path."""
    trace_id = str(trace.get("trace_id") or "")
    if not _TRACE_ID.fullmatch(trace_id) or str(trace.get("task_type") or "").startswith("eval"):
        return None
    path = _drafts_dir(config_root) / f"{trace_id}.yaml"
    if path.exists():
        return path
    outcome = next((score for score in trace.get("scores", []) if score.get("name") == "outcome"), {})
    draft = {
        "id": f"from-{trace_id[4:16]}",
        "task": redact_secrets(str(trace.get("input") or ""), 2000),
        "split": "train",
        "tags": ["from-trace", str(trace.get("task_type") or "chat")],
        "fixture": {
            path_name: "# TODO: minimal content that reproduces the problem\n" for path_name in touched_paths(trace)
        },
        "accept": "TODO: a command that exits 0 only when the task is done correctly",
        "allowed_commands": [],
        "source_trace": trace_id,
        "source_outcome": outcome.get("value"),
        "source_comment": outcome.get("comment", ""),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(draft, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def list_drafts(config_root: Path | str) -> list[dict[str, Any]]:
    directory = _drafts_dir(config_root)
    if not directory.is_dir():
        return []
    drafts = []
    for path in sorted(directory.glob("trc_*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        drafts.append({"trace_id": path.stem, **data})
    return drafts


def save_draft_as_case(config_root: Path | str, trace_id: str, case: dict[str, Any]) -> Path:
    """Validate the user's completed case and move it into the project's cases folder."""
    if not _TRACE_ID.fullmatch(trace_id):
        raise EvalCaseError("Unknown draft.")
    if "TODO" in str(case.get("accept", "")):
        raise EvalCaseError("Replace the TODO acceptance command with a real check first.")
    parsed = parse_case(case, f"draft {trace_id}")
    target = Path(config_root) / ".agents" / "evals" / "cases" / f"{parsed.case_id}.yaml"
    if target.exists():
        raise EvalCaseError(f"A case named {parsed.case_id!r} already exists.")
    target.parent.mkdir(parents=True, exist_ok=True)
    clean = {key: value for key, value in case.items() if not key.startswith("source_")}
    target.write_text(yaml.safe_dump(clean, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (_drafts_dir(config_root) / f"{trace_id}.yaml").unlink(missing_ok=True)
    return target

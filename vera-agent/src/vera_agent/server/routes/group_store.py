"""Shared helpers for group routes: state access, project resolution, and JSON persistence.

Instances are stored at `<project>/.agents/groups/<group_id>.json` and runs at
`<project>/.agents/runs/<group_id>/<run_id>.json`; writes go through a temporary file and an atomic replace.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from starlette.requests import Request

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.groups")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _project_root(state: ServerState, project_id: str | None) -> Path:
    return state.get_project_root(project_id)


def _groups_dir(project_root: Path) -> Path:
    return project_root / ".agents" / "groups"


def _load_group(project_root: Path, group_id: str) -> dict[str, Any] | None:
    group_file = _groups_dir(project_root) / f"{group_id}.json"
    if not group_file.exists():
        return None
    try:
        return json.loads(group_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_group(project_root: Path, group: dict[str, Any]) -> None:
    group_dir = _groups_dir(project_root)
    group_dir.mkdir(parents=True, exist_ok=True)
    target = group_dir / f"{group['group_id']}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(group, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def _save_run(run_file: Path, run: dict[str, Any]) -> None:
    run_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = run_file.with_name(f"{run_file.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(run_file)

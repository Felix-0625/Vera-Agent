"""Persistent user rules and context settings, plus the user-profile memory API kept for older clients.

User-profile memories are stored by the scoped memory layer (`vera_agent/memory/`) in the user
scope. The functions below keep the `/api/settings/user-memories` shape (``id``, ``category``)
and the `remember_user` / `forget_user_memory` tool behaviour on top of it.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from vera_agent.memory.records import USER_KINDS
from vera_agent.memory.service import MemoryWriteError, memory_service_for_state

_LOCK = threading.RLock()


def _data_dir(state: Any) -> Path:
    return Path(state.projects_config_root) / ".agents"


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_context_settings(state: Any) -> dict[str, Any]:
    with _LOCK:
        value = _load_json(_data_dir(state) / "user_context.json", {})
    if not isinstance(value, dict):
        value = {}
    return {
        "user_rules": value.get("user_rules", "") if isinstance(value.get("user_rules", ""), str) else "",
        "include_agents_md": value.get("include_agents_md", True) is True,
        "memory_enabled": value.get("memory_enabled", True) is True,
    }


def save_context_settings(state: Any, updates: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        value = _load_json(_data_dir(state) / "user_context.json", {})
        current = value if isinstance(value, dict) else {}
        current = {
            "user_rules": current.get("user_rules", "") if isinstance(current.get("user_rules", ""), str) else "",
            "include_agents_md": current.get("include_agents_md", True) is True,
            "memory_enabled": current.get("memory_enabled", True) is True,
        }
        current.update(updates)
        _save_json(_data_dir(state) / "user_context.json", current)
    return current


def load_user_memories(state: Any) -> list[dict[str, Any]]:
    """Active user-scope profile memories, newest first (at most 200)."""
    records = memory_service_for_state(state).backend.list([("user", "")], kinds=list(USER_KINDS))
    return [record.to_legacy_dict() for record in records[:200]]


def upsert_user_memory(
    state: Any,
    category: str,
    content: str,
    *,
    memory_id: str | None = None,
    source_thread_id: str | None = None,
    source: str = "agent",
    require_existing: bool = False,
) -> dict[str, Any]:
    """Create or revise a user-profile memory; raises ValueError (invalid) or LookupError (unknown id)."""
    if category not in USER_KINDS:
        raise ValueError("Unsupported user memory category.")
    service = memory_service_for_state(state)
    existing = service.backend.get(memory_id) if memory_id else None
    if memory_id and (existing is None or existing.status == "deleted" or existing.scope != "user"):
        if require_existing:
            raise LookupError("Memory not found.")
        existing = None
    try:
        if existing is not None:
            record = service.revise(
                existing.memory_id, content, actor=source, kind=category, thread_id=source_thread_id or ""
            )
        else:
            record = service.add(
                scope="user", kind=category, content=content, source=source, thread_id=source_thread_id or ""
            )
    except MemoryWriteError as error:
        raise ValueError(str(error)) from error
    return record.to_legacy_dict()


def delete_user_memory(state: Any, memory_id: str) -> bool:
    service = memory_service_for_state(state)
    record = service.backend.get(memory_id)
    if record is None or record.scope != "user" or record.kind not in USER_KINDS:
        return False
    return service.delete(memory_id, actor="user")

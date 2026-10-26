"""The single write path for memories, pending changes, and the legacy user-memory migration.

Every write goes through `MemoryService`, which enforces the content limit and the secret filter
(`utils/redact.py`) before anything reaches a backend. Automatic consolidation never deletes or
overwrites directly: an UPDATE or DELETE proposed by the model becomes a pending change that the
user confirms in the memory panel, or that applies itself after ``auto_apply_seconds`` when the
user enabled that (it stays undoable through the version history either way).

On first use, `memory_service_for_state` imports the legacy `user_memories.json` into the user
scope once; the old file is left in place untouched.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from vera_agent.memory.backend import MemoryBackend, SqliteMemoryBackend
from vera_agent.memory.records import KINDS, MAX_CONTENT_CHARS, MAX_RULE_CHARS, SCOPES, USER_KINDS, MemoryRecord
from vera_agent.utils.redact import contains_secret

MEMORY_DB_FILE = "memory.db"
# Who may write which kind: a rule changes agent behaviour, so the model can never write one.
_AGENT_WRITABLE_KINDS = {*USER_KINDS, "fact", "episode"}


class MemoryWriteError(ValueError):
    """A memory write was rejected (invalid scope or kind, too long, or contains a secret)."""


def normalize_content(content: str, kind: str = "") -> str:
    """Validated memory text. Rules are stored byte-for-byte (only a length and secret check): the
    eval gate and the active profile both render rule content with the same function, so any
    transformation here would make what the gate measured differ from what adoption stores. Every
    other kind is folded to one line of 500 chars."""
    if kind == "rule":
        content = str(content).strip("\n")
        limit = MAX_RULE_CHARS
    else:
        content = re.sub(r"\s+", " ", str(content)).strip()
        limit = MAX_CONTENT_CHARS
    if not content or len(content) > limit:
        raise MemoryWriteError(f"Memory content must contain 1 to {limit} characters.")
    if contains_secret(content):
        raise MemoryWriteError("Memory content cannot contain credentials or secret values.")
    return content


class MemoryService:
    def __init__(
        self,
        backend: MemoryBackend,
        pending_store: SqliteMemoryBackend,
        *,
        auto_apply_seconds: float | None = None,
    ):
        """``pending_store`` keeps pending changes; it is the backend itself for the default SQLite store,
        and a local SQLite file next to it when records live in Mem0."""
        self.backend = backend
        self.pending_store = pending_store
        self.auto_apply_seconds = auto_apply_seconds

    # --- direct writes (user, explicit tool calls, adoption) -------------------------------

    def add(
        self,
        *,
        scope: str,
        kind: str,
        content: str,
        scope_id: str = "",
        source: str = "agent",
        confidence: float = 1.0,
        thread_id: str = "",
        trace_id: str = "",
        reason: str = "created",
    ) -> MemoryRecord:
        if scope not in SCOPES or kind not in KINDS:
            raise MemoryWriteError("Unsupported memory scope or kind.")
        if kind == "rule" and source not in {"user", "adoption", "adoption:overlay", "profile"}:
            raise MemoryWriteError("Rules can only be written by the user or an approved adoption.")
        if source == "agent" and kind not in _AGENT_WRITABLE_KINDS:
            raise MemoryWriteError("The agent cannot write this kind of memory.")
        content = normalize_content(content, kind)
        scope_id = "" if scope == "user" else str(scope_id)
        duplicate = next(
            (
                item
                for item in self.backend.list([(scope, scope_id)], kinds=[kind])
                if item.content.casefold() == content.casefold()
            ),
            None,
        )
        if duplicate is not None:
            return duplicate
        record = MemoryRecord(
            memory_id="",
            scope=scope,
            scope_id=scope_id,
            kind=kind,
            content=content,
            confidence=max(0.0, min(1.0, float(confidence))),
            source=source,
            source_thread_id=thread_id,
            source_trace_id=trace_id,
        )
        return self.backend.insert(record, reason=reason, actor=source)

    def revise(
        self,
        memory_id: str,
        content: str,
        *,
        actor: str,
        reason: str = "revised",
        kind: str | None = None,
        trace_id: str = "",
        thread_id: str = "",
    ) -> MemoryRecord:
        current = self.backend.get(memory_id)
        if current is None or current.status == "deleted":
            raise LookupError("Memory not found.")
        if current.kind == "rule" and actor not in {"user", "adoption"}:
            raise MemoryWriteError("Rules can only be revised by the user.")
        if kind is not None and kind not in KINDS:
            raise MemoryWriteError("Unsupported memory kind.")
        # A rule changes every turn; turning another memory into one (or back) bypasses add()'s check.
        if kind is not None and (kind == "rule") != (current.kind == "rule"):
            raise MemoryWriteError("A memory cannot be changed into or out of a rule; create a new rule instead.")
        return self.backend.update(
            memory_id,
            content=normalize_content(content, kind or current.kind),
            kind=kind,
            status="active",
            reason=reason,
            actor=actor,
            trace_id=trace_id,
            thread_id=thread_id,
        )

    def delete(self, memory_id: str, *, actor: str, reason: str = "deleted", trace_id: str = "") -> bool:
        current = self.backend.get(memory_id)
        if current is None or current.status == "deleted":
            return False
        self.backend.update(memory_id, status="deleted", reason=reason, actor=actor, trace_id=trace_id)
        return True

    def restore_version(self, memory_id: str, version: int, *, actor: str = "user") -> MemoryRecord:
        """Undo: make an earlier version current again (as a new version, so nothing is lost)."""
        entry = next((item for item in self.backend.history(memory_id) if item["version"] == version), None)
        if entry is None:
            raise LookupError("Memory version not found.")
        return self.backend.update(
            memory_id,
            content=entry["content"],
            kind=entry["kind"],
            status="active",
            reason=f"restored version {version}",
            actor=actor,
        )

    # --- pending changes (proposed by consolidation) ----------------------------------------

    def propose_change(
        self,
        operation: str,
        *,
        memory_id: str = "",
        scope: str = "",
        scope_id: str = "",
        kind: str = "",
        content: str = "",
        reason: str = "",
        trace_id: str = "",
        thread_id: str = "",
    ) -> dict[str, Any]:
        if operation not in {"update", "delete"}:
            raise MemoryWriteError("Only update and delete changes wait for confirmation.")
        if operation == "update":
            content = normalize_content(content)
        target = self.backend.get(memory_id)
        if target is None or target.status != "active":
            raise LookupError("Memory not found.")
        if target.kind == "rule":
            raise MemoryWriteError("Consolidation never changes rules.")
        now = time.time()
        change = {
            "change_id": f"chg_{uuid.uuid4().hex[:12]}",
            "operation": operation,
            "memory_id": memory_id,
            "scope": scope or target.scope,
            "scope_id": scope_id or target.scope_id,
            "kind": kind or target.kind,
            "content": content,
            "reason": reason[:300],
            "trace_id": trace_id,
            "thread_id": thread_id,
            "status": "pending",
            "apply_after": now + self.auto_apply_seconds if self.auto_apply_seconds is not None else None,
            "created_at": now,
            "resolved_at": None,
        }
        with self.pending_store.connect() as connection:
            connection.execute(
                f"INSERT INTO pending_changes ({', '.join(change)}) VALUES ({', '.join('?' * len(change))})",
                list(change.values()),
            )
        return change

    def pending_changes(self, status: str = "pending") -> list[dict[str, Any]]:
        with self.pending_store.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM pending_changes WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        changes = [dict(row) for row in rows]
        for change in changes:
            target = self.backend.get(change["memory_id"])
            change["current_content"] = target.content if target else ""
        return changes

    def resolve_change(self, change_id: str, accept: bool, *, actor: str = "user") -> dict[str, Any]:
        with self.pending_store.connect() as connection:
            row = connection.execute("SELECT * FROM pending_changes WHERE change_id = ?", (change_id,)).fetchone()
        if row is None or row["status"] != "pending":
            raise LookupError("Pending change not found.")
        change = dict(row)
        if accept:
            reason = f"consolidation: {change['reason']}" if change["reason"] else "consolidation"
            if change["operation"] == "update":
                self.revise(
                    change["memory_id"],
                    change["content"],
                    actor=actor,
                    reason=reason,
                    trace_id=change["trace_id"] or "",
                    thread_id=change["thread_id"] or "",
                )
            else:
                self.delete(change["memory_id"], actor=actor, reason=reason, trace_id=change["trace_id"] or "")
        change["status"] = "accepted" if accept else "rejected"
        with self.pending_store.connect() as connection:
            connection.execute(
                "UPDATE pending_changes SET status = ?, resolved_at = ? WHERE change_id = ?",
                (change["status"], time.time(), change_id),
            )
        return change

    def apply_due_changes(self) -> int:
        """Apply pending changes whose undo window passed (only when auto-apply is enabled)."""
        with self.pending_store.connect() as connection:
            rows = connection.execute(
                "SELECT change_id FROM pending_changes WHERE status = 'pending' AND apply_after IS NOT NULL "
                "AND apply_after <= ?",
                (time.time(),),
            ).fetchall()
        applied = 0
        for row in rows:
            try:
                self.resolve_change(row["change_id"], True, actor="auto")
                applied += 1
            except (LookupError, MemoryWriteError):
                continue
        return applied


MEMORY_CONFIG_FILE = "memory_config.json"
DEFAULT_MEMORY_CONFIG: dict[str, Any] = {
    "backend": "sqlite",
    "consolidation": "off",
    "consolidation_model_id": "",
    "auto_apply_hours": None,
    "embedding_model": "",
    "rerank_model": "",
    "token_budget": 150,
    "rule_token_budget": 120,
}


def load_memory_config(state: Any) -> dict[str, Any]:
    """Memory settings; consolidation is off by default because each run costs a model call."""
    path = Path(state.projects_config_root) / ".agents" / MEMORY_CONFIG_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        raw = {}
    config = dict(DEFAULT_MEMORY_CONFIG)
    if isinstance(raw, dict):
        config.update({key: raw[key] for key in DEFAULT_MEMORY_CONFIG if key in raw})
    if config["consolidation"] not in {"off", "task_end"}:
        config["consolidation"] = "off"
    if config["backend"] not in {"sqlite", "mem0"}:
        config["backend"] = "sqlite"
    for key in ("token_budget", "rule_token_budget"):
        try:
            config[key] = max(40, min(int(config[key]), 2000))
        except (TypeError, ValueError):
            config[key] = DEFAULT_MEMORY_CONFIG[key]
    return config


def save_memory_config(state: Any, updates: dict[str, Any]) -> dict[str, Any]:
    current = load_memory_config(state)
    current.update({key: value for key, value in updates.items() if key in DEFAULT_MEMORY_CONFIG})
    path = Path(state.projects_config_root) / ".agents" / MEMORY_CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_memory_config(state)


def _migrate_legacy_user_memories(service: MemoryService, config_dir: Path) -> None:
    marker = config_dir / "memory_migrated_v1"
    legacy = config_dir / "user_memories.json"
    if marker.exists():
        return
    try:
        items = json.loads(legacy.read_text(encoding="utf-8")).get("memories", []) if legacy.is_file() else []
    except (OSError, json.JSONDecodeError, AttributeError):
        items = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("category") not in USER_KINDS:
            continue
        try:
            record = service.add(
                scope="user",
                kind=item["category"],
                content=str(item.get("content", "")),
                source="user" if item.get("source") == "user" else "agent",
                thread_id=str(item.get("source_thread_id") or ""),
                reason="imported from user_memories.json",
            )
        except MemoryWriteError:
            continue
        # Keep the legacy id usable by older clients and by the model's earlier tool calls.
        if item.get("id") and record.memory_id != item["id"]:
            with service.pending_store.connect() as connection:
                for table in ("memories", "memory_versions", "memory_fts"):
                    connection.execute(
                        f"UPDATE {table} SET memory_id = ? WHERE memory_id = ?", (item["id"], record.memory_id)
                    )
    marker.write_text("1", encoding="utf-8")


def memory_service_for_state(state: Any) -> MemoryService:
    config_dir = Path(state.projects_config_root) / ".agents"
    config = load_memory_config(state)
    local = SqliteMemoryBackend(config_dir / MEMORY_DB_FILE)
    backend: MemoryBackend = local
    if config["backend"] == "mem0":
        from vera_agent.memory.mem0_backend import Mem0Backend

        backend = Mem0Backend.from_config(state, local)
    hours = config["auto_apply_hours"]
    service = MemoryService(backend, local, auto_apply_seconds=float(hours) * 3600 if hours not in (None, "") else None)
    _migrate_legacy_user_memories(service, config_dir)
    return service

"""Optional Mem0 backend: keeps memory records in a user-configured Mem0 instance.

Enable with `memory_config.json` ``{"backend": "mem0"}`` and install ``mem0ai`` yourself; it is
not a VeraAgent dependency. Mem0's default configuration calls an external LLM and embedding
API for every write, so point it at a local setup (``mem0_config`` in `memory_config.json` is
passed to ``Memory.from_config``) if conversations must stay on this machine.

Mem0 stores the content and its own vectors; VeraAgent's scope, kind, version and status fields
travel in Mem0 metadata. Version history and pending changes stay in the local SQLite file, so
the memory panel, undo and confirmation work the same with either backend. VeraAgent passes
``infer=False`` so Mem0 does not run a second, unreviewed consolidation of its own.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from vera_agent.memory.backend import SqliteMemoryBackend
from vera_agent.memory.records import MemoryRecord

_USER_ID = "vera-local"


class Mem0Backend:
    """Records in Mem0; history and pending changes delegated to ``local``."""

    def __init__(self, memory: Any, local: SqliteMemoryBackend):
        self.memory = memory
        self.local = local

    @classmethod
    def from_config(cls, state: Any, local: SqliteMemoryBackend) -> Mem0Backend:
        try:
            from mem0 import Memory
        except ImportError as error:
            raise RuntimeError("The Mem0 backend needs the mem0ai package: uv pip install mem0ai") from error
        path = Path(state.projects_config_root) / ".agents" / "memory_config.json"
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        config = raw.get("mem0_config") if isinstance(raw.get("mem0_config"), dict) else None
        return cls(Memory.from_config(config) if config else Memory(), local)

    def connect(self):
        return self.local.connect()

    @staticmethod
    def _record(item: dict[str, Any]) -> MemoryRecord:
        meta = item.get("metadata") or {}
        return MemoryRecord(
            memory_id=str(item.get("id")),
            scope=str(meta.get("scope", "user")),
            scope_id=str(meta.get("scope_id", "")),
            kind=str(meta.get("kind", "fact")),
            content=str(item.get("memory") or ""),
            status=str(meta.get("status", "active")),
            version=int(meta.get("version", 1)),
            confidence=float(meta.get("confidence", 1.0)),
            source=str(meta.get("source", "agent")),
            source_thread_id=str(meta.get("source_thread_id", "")),
            source_trace_id=str(meta.get("source_trace_id", "")),
            created_at=float(meta.get("created_at", 0.0)),
            updated_at=float(meta.get("updated_at", 0.0)),
        )

    def _all(self) -> list[MemoryRecord]:
        response = self.memory.get_all(user_id=_USER_ID)
        items = response.get("results", response) if isinstance(response, dict) else response
        return [self._record(item) for item in items or []]

    @staticmethod
    def _metadata(record: MemoryRecord) -> dict[str, Any]:
        return {key: value for key, value in record.to_dict().items() if key not in {"memory_id", "content"}}

    def get(self, memory_id: str) -> MemoryRecord | None:
        item = self.memory.get(memory_id)
        return self._record(item) if item else None

    def scopes(self) -> list[tuple[str, str]]:
        return sorted({(record.scope, record.scope_id) for record in self._all()})

    def list(self, scopes, *, kinds=None, status="active") -> list[MemoryRecord]:
        wanted = set(scopes)
        records = [
            record
            for record in self._all()
            if (record.scope, record.scope_id) in wanted
            and (status == "any" or record.status == status)
            and (not kinds or record.kind in kinds)
        ]
        return sorted(records, key=lambda record: record.updated_at, reverse=True)

    def insert(self, record: MemoryRecord, *, reason: str, actor: str) -> MemoryRecord:
        now = time.time()
        record.created_at = record.created_at or now
        record.updated_at = record.updated_at or now
        response = self.memory.add(record.content, user_id=_USER_ID, metadata=self._metadata(record), infer=False)
        results = response.get("results", []) if isinstance(response, dict) else response
        record.memory_id = str(results[0]["id"]) if results else f"mem_{uuid.uuid4().hex[:12]}"
        with self.local.connect() as connection:
            self.local._write_version(
                connection,
                record,
                reason=reason,
                actor=actor,
                trace_id=record.source_trace_id,
                thread_id=record.source_thread_id,
            )
        return record

    def update(self, memory_id, *, content=None, kind=None, status=None, reason, actor, trace_id="", thread_id=""):
        record = self.get(memory_id)
        if record is None:
            raise LookupError("Memory not found.")
        record.content = content if content is not None else record.content
        record.kind = kind or record.kind
        record.status = status or record.status
        record.version += 1
        record.updated_at = time.time()
        # Mem0's update() replaces only the text, so a metadata change (status, kind, version) is
        # written as delete + add under the same content; the local history keeps the id chain.
        self.memory.delete(memory_id)
        response = self.memory.add(record.content, user_id=_USER_ID, metadata=self._metadata(record), infer=False)
        results = response.get("results", []) if isinstance(response, dict) else response
        if results:
            new_id = str(results[0]["id"])
            with self.local.connect() as connection:
                connection.execute("UPDATE memory_versions SET memory_id = ? WHERE memory_id = ?", (new_id, memory_id))
            record.memory_id = new_id
        with self.local.connect() as connection:
            self.local._write_version(
                connection, record, reason=reason, actor=actor, trace_id=trace_id, thread_id=thread_id
            )
        return record

    def history(self, memory_id: str) -> list[dict[str, Any]]:
        return self.local.history(memory_id)

    def keyword_search(self, query: str, scopes, limit: int) -> list[tuple[MemoryRecord, float]]:
        response = self.memory.search(query, user_id=_USER_ID, limit=limit * 3)
        items = response.get("results", response) if isinstance(response, dict) else response
        wanted = set(scopes)
        hits = [(self._record(item), float(item.get("score") or 0.0)) for item in items or []]
        return [
            (record, score)
            for record, score in hits
            if (record.scope, record.scope_id) in wanted and record.status == "active"
        ][:limit]

    def vector_search(self, vector: list[float], scopes, limit: int) -> list[tuple[MemoryRecord, float]]:
        # Mem0 searches with its own embedder; keyword_search already uses it.
        return []

    def set_embedding(self, memory_id: str, model: str, vector: list[float]) -> None:
        return None

    def mark_used(self, memory_ids: list[str]) -> None:
        return None

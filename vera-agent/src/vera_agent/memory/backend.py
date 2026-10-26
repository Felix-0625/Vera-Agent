"""Memory storage: the `MemoryBackend` protocol and the default local SQLite backend.

`SqliteMemoryBackend` keeps every version of a memory: an update writes a new row in
``memory_versions`` and bumps ``version``; a delete only sets ``status = 'deleted'``. Each version
records why it changed (``reason``) and which trace or thread caused it. Keyword search uses an
FTS5 table with the ``trigram`` tokenizer, which matches Chinese text without a word segmenter
(queries shorter than three characters fall back to ``LIKE``). Embeddings, when a model provides
them, are stored as JSON arrays and compared with cosine similarity in Python.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

from vera_agent.memory.records import MemoryRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    scope_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    source_thread_id TEXT,
    source_trace_id TEXT,
    created_at REAL,
    updated_at REAL,
    last_used_at REAL DEFAULT 0,
    use_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS memories_scope ON memories(scope, scope_id, status);
CREATE TABLE IF NOT EXISTS memory_versions (
    memory_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT,
    kind TEXT,
    status TEXT,
    reason TEXT,
    actor TEXT,
    trace_id TEXT,
    thread_id TEXT,
    changed_at REAL,
    PRIMARY KEY (memory_id, version)
);
CREATE TABLE IF NOT EXISTS memory_embeddings (
    memory_id TEXT PRIMARY KEY,
    model TEXT,
    vector TEXT
);
CREATE TABLE IF NOT EXISTS pending_changes (
    change_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    memory_id TEXT,
    scope TEXT,
    scope_id TEXT,
    kind TEXT,
    content TEXT,
    reason TEXT,
    trace_id TEXT,
    thread_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    apply_after REAL,
    created_at REAL,
    resolved_at REAL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(memory_id UNINDEXED, content, tokenize='trigram');
"""

_LOCK = threading.RLock()
_RECORD_FIELDS = tuple(MemoryRecord.__dataclass_fields__)


class MemoryBackend(Protocol):
    """Storage operations the memory service needs; implemented by SQLite (default) and Mem0."""

    def get(self, memory_id: str) -> MemoryRecord | None: ...

    def scopes(self) -> list[tuple[str, str]]: ...

    def list(
        self, scopes: list[tuple[str, str]], *, kinds: list[str] | None = None, status: str = "active"
    ) -> list[MemoryRecord]: ...

    def insert(self, record: MemoryRecord, *, reason: str, actor: str) -> MemoryRecord: ...

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        reason: str,
        actor: str,
        trace_id: str = "",
        thread_id: str = "",
    ) -> MemoryRecord: ...

    def history(self, memory_id: str) -> list[dict[str, Any]]: ...

    def keyword_search(
        self, query: str, scopes: list[tuple[str, str]], limit: int
    ) -> list[tuple[MemoryRecord, float]]: ...

    def vector_search(
        self, vector: list[float], scopes: list[tuple[str, str]], limit: int
    ) -> list[tuple[MemoryRecord, float]]: ...

    def set_embedding(self, memory_id: str, model: str, vector: list[float]) -> None: ...

    def mark_used(self, memory_ids: list[str]) -> None: ...


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def _scope_clause(scopes: list[tuple[str, str]], alias: str = "m") -> tuple[str, list[str]]:
    if not scopes:
        return "0", []
    parts = " OR ".join(f"({alias}.scope = ? AND {alias}.scope_id = ?)" for _ in scopes)
    return f"({parts})", [value for pair in scopes for value in pair]


_CJK_RUN = re.compile(r"[㐀-鿿豈-﫿]+")
_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]{2,}")


def query_terms(query: str, max_terms: int = 24) -> list[str]:
    """Search terms for the trigram index: Latin words of 3+ characters and 3-character windows of
    Chinese runs (a Chinese sentence has no spaces, so whole-phrase matching would rarely hit)."""
    terms: list[str] = [word.casefold() for word in _WORD.findall(query)]
    for run in _CJK_RUN.findall(query):
        if len(run) <= 3:
            terms.append(run)
        else:
            terms.extend(run[index : index + 3] for index in range(len(run) - 2))
    return list(dict.fromkeys(terms))[:max_terms]


def _term_coverage(terms: list[str], content: str) -> float:
    """Matched query terms over the smaller of the query's and the memory's term counts, in [0, 1].

    Dividing by the smaller count keeps a short memory that matches fully from scoring low just
    because the question was long."""
    text = content.casefold()
    matched = sum(term in text for term in terms)
    return matched / max(1, min(len(terms), len(query_terms(content))))


def _fts_query(terms: list[str]) -> str:
    # OR keeps recall broad; bm25 ranks memories that share more terms higher.
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)


class SqliteMemoryBackend:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(_SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            **{name: row[name] if row[name] is not None else "" for name in _RECORD_FIELDS}
            | {
                "confidence": float(row["confidence"] or 0.0),
                "version": int(row["version"] or 1),
                "created_at": float(row["created_at"] or 0.0),
                "updated_at": float(row["updated_at"] or 0.0),
                "last_used_at": float(row["last_used_at"] or 0.0),
                "use_count": int(row["use_count"] or 0),
            }
        )

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        return self._record(row) if row else None

    def scopes(self) -> list[tuple[str, str]]:
        """Every (scope, scope_id) pair that holds at least one memory."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT scope, scope_id FROM memories ORDER BY scope, scope_id"
            ).fetchall()
        return [(row["scope"], row["scope_id"]) for row in rows]

    def list(self, scopes, *, kinds=None, status="active") -> list[MemoryRecord]:
        clause, params = _scope_clause(scopes)
        sql = f"SELECT * FROM memories m WHERE {clause}"
        if status != "any":
            sql += " AND m.status = ?"
            params.append(status)
        if kinds:
            sql += f" AND m.kind IN ({', '.join('?' * len(kinds))})"
            params.extend(kinds)
        with self.connect() as connection:
            rows = connection.execute(sql + " ORDER BY m.updated_at DESC", params).fetchall()
        return [self._record(row) for row in rows]

    @staticmethod
    def _write_version(connection, record: MemoryRecord, *, reason: str, actor: str, trace_id: str, thread_id: str):
        connection.execute(
            "INSERT OR REPLACE INTO memory_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.memory_id,
                record.version,
                record.content,
                record.kind,
                record.status,
                reason,
                actor,
                trace_id,
                thread_id,
                time.time(),
            ),
        )

    @staticmethod
    def _sync_fts(connection, record: MemoryRecord) -> None:
        connection.execute("DELETE FROM memory_fts WHERE memory_id = ?", (record.memory_id,))
        if record.status == "active":
            connection.execute("INSERT INTO memory_fts VALUES (?, ?)", (record.memory_id, record.content.casefold()))

    def insert(self, record: MemoryRecord, *, reason: str, actor: str) -> MemoryRecord:
        now = time.time()
        record.memory_id = record.memory_id or f"mem_{uuid.uuid4().hex[:12]}"
        record.created_at = record.created_at or now
        record.updated_at = record.updated_at or now
        with _LOCK, self.connect() as connection:
            values = record.to_dict()
            connection.execute(
                f"INSERT INTO memories ({', '.join(_RECORD_FIELDS)}) VALUES ({', '.join('?' * len(_RECORD_FIELDS))})",
                [values[name] for name in _RECORD_FIELDS],
            )
            self._write_version(
                connection,
                record,
                reason=reason,
                actor=actor,
                trace_id=record.source_trace_id,
                thread_id=record.source_thread_id,
            )
            self._sync_fts(connection, record)
        return record

    def update(self, memory_id, *, content=None, kind=None, status=None, reason, actor, trace_id="", thread_id=""):
        with _LOCK, self.connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
            if row is None:
                raise LookupError("Memory not found.")
            record = self._record(row)
            record.content = content if content is not None else record.content
            record.kind = kind or record.kind
            record.status = status or record.status
            record.version += 1
            record.updated_at = time.time()
            if trace_id:
                record.source_trace_id = trace_id
            connection.execute(
                "UPDATE memories SET content = ?, kind = ?, status = ?, version = ?, updated_at = ?, "
                "source_trace_id = ? WHERE memory_id = ?",
                (
                    record.content,
                    record.kind,
                    record.status,
                    record.version,
                    record.updated_at,
                    record.source_trace_id,
                    memory_id,
                ),
            )
            self._write_version(connection, record, reason=reason, actor=actor, trace_id=trace_id, thread_id=thread_id)
            self._sync_fts(connection, record)
            if content is not None:
                connection.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,))
        return record

    def history(self, memory_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM memory_versions WHERE memory_id = ? ORDER BY version", (memory_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def keyword_search(self, query: str, scopes, limit: int) -> list[tuple[MemoryRecord, float]]:
        # The trigram tokenizer only indexes runs of 3+ characters (sqlite.org/fts5.html#the_trigram_tokenizer),
        # so a 1-2 character CJK term (query_terms keeps short runs whole) can never MATCH. Those
        # terms get their own literal-substring pass, merged with the FTS pass for the rest: a mixed
        # A mixed query must keep its short terms; an all-short query must match terms separately.
        # must not fall back to matching the whole phrase as one literal string.
        all_terms = query_terms(query)
        long_terms = [term for term in all_terms if len(term) >= 3]
        short_terms = [term for term in all_terms if len(term) < 3]
        clause, params = _scope_clause(scopes)
        if not all_terms:
            return []
        candidates: dict[str, MemoryRecord] = {}
        with self.connect() as connection:
            if long_terms:
                rows = connection.execute(
                    f"SELECT m.*, bm25(memory_fts) AS rank FROM memory_fts JOIN memories m "
                    f"ON m.memory_id = memory_fts.memory_id WHERE memory_fts MATCH ? AND m.status = 'active' "
                    f"AND {clause} ORDER BY rank LIMIT ?",
                    (_fts_query(long_terms), *params, limit),
                ).fetchall()
                candidates.update((row["memory_id"], self._record(row)) for row in rows)
            for term in short_terms:
                rows = connection.execute(
                    f"SELECT * FROM memories m WHERE m.status = 'active' AND {clause} "
                    f"AND lower(m.content) LIKE ? LIMIT ?",
                    (*params, f"%{term.casefold()}%", limit),
                ).fetchall()
                candidates.update((row["memory_id"], self._record(row)) for row in rows)
        # bm25 orders the FTS candidates, but its value depends on corpus size (near zero with a few
        # memories), so relevance is the share of matched query terms (over all terms, long and
        # short) instead, consistently for every candidate regardless of which pass found it.
        scored = [(record, _term_coverage(all_terms, record.content)) for record in candidates.values()]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

    def vector_search(self, vector: list[float], scopes, limit: int) -> list[tuple[MemoryRecord, float]]:
        clause, params = _scope_clause(scopes)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT m.*, e.vector FROM memories m JOIN memory_embeddings e ON e.memory_id = m.memory_id "
                f"WHERE m.status = 'active' AND {clause}",
                params,
            ).fetchall()
        scored = [(self._record(row), _cosine(vector, json.loads(row["vector"]))) for row in rows]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

    def set_embedding(self, memory_id: str, model: str, vector: list[float]) -> None:
        with _LOCK, self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO memory_embeddings VALUES (?, ?, ?)", (memory_id, model, json.dumps(vector))
            )

    def mark_used(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        with _LOCK, self.connect() as connection:
            connection.executemany(
                "UPDATE memories SET use_count = use_count + 1, last_used_at = ? WHERE memory_id = ?",
                [(time.time(), memory_id) for memory_id in memory_ids],
            )

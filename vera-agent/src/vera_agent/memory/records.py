"""Memory scopes, kinds and the record shape shared by every backend.

Scopes nest from broad to narrow: ``user`` (every conversation), ``project`` (one project, keyed
by project id) and ``session`` (one thread). Kinds:

- ``profile``, ``preference``, ``habit``, ``feedback``: facts about the user (the legacy categories).
- ``fact``: a durable project fact (conventions, decisions, known pitfalls).
- ``episode``: what happened in one finished task (goal, process, pitfalls, solution, score).
- ``rule``: an instruction approved by the user, usually adopted from an evolution proposal.
  Rules are recalled with their own budget and can only be written by the user or an adoption.

Status is ``active``, ``superseded`` (replaced by a newer version) or ``deleted`` (soft delete).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCOPES = ("user", "project", "session")
USER_KINDS = ("profile", "preference", "habit", "feedback")
KINDS = (*USER_KINDS, "fact", "episode", "rule")
STATUSES = ("active", "superseded", "deleted")
MAX_CONTENT_CHARS = 500
# Rules hold adopted rules and prompt overlays; matches the Critic's overlay limit.
MAX_RULE_CHARS = 1500


@dataclass
class MemoryRecord:
    memory_id: str
    scope: str
    scope_id: str
    kind: str
    content: str
    status: str = "active"
    version: int = 1
    confidence: float = 1.0
    source: str = "agent"
    source_thread_id: str = ""
    source_trace_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    last_used_at: float = 0.0
    use_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_legacy_dict(self) -> dict[str, Any]:
        """The `/api/settings/user-memories` shape (``id`` and ``category``) kept for older clients."""
        value = {
            "id": self.memory_id,
            "category": self.kind,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
        }
        if self.source_thread_id:
            value["source_thread_id"] = self.source_thread_id
        return value

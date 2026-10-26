"""Scoped, versioned long-term memory (replaces the flat list in `server/user_context.py`).

- `records.py`: scopes, kinds and the `MemoryRecord` shape.
- `backend.py`: the `MemoryBackend` protocol and the default SQLite + FTS5 (trigram) backend.
- `service.py`: the write path (secret filter, versions, pending changes) and legacy migration.
- `retrieve.py`: hybrid keyword/vector recall within a token budget, rendered as `<runtime_memory>`.
- `consolidate.py`: Mem0-style consolidation after a turn, and episodic memories from traces.
- `mem0_backend.py`: optional adapter to a local Mem0 installation; never the default.

Memories live in `<projects_config_root>/.agents/memory.db`.
"""

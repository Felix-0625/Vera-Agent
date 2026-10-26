"""Local traces, spans and scores for chat turns (data model follows Langfuse's trace/observation/score).

- `trace.py`: `Trace`, `Span`, `Score` records and the per-turn `TurnTracer`.
- `store.py`: SQLite persistence in `<config root>/.agents/traces.db`.
- `scoring.py`: outcome scores from turn signals, the next user message, and final test runs.
- `exporters/langfuse.py`: optional export to a Langfuse server; disabled by default.
"""

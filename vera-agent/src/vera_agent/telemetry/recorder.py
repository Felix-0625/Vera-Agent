"""Attach a tracer to a desktop chat turn and persist, score and export it when the turn ends.

Settings live in `<projects_config_root>/.agents/telemetry_config.json`:
``{"enabled": true, "langfuse": {"enabled": false, "host": "...", "public_key": "...", "secret_key": "..."}}``.
Tracing is on by default and stays local; the Langfuse exporter runs only when explicitly enabled.
Ephemeral side conversations are never traced.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from vera_agent.telemetry.scoring import followup_score, score_finished_trace
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Trace, TurnTracer, classify_task_type

logger = logging.getLogger("vera_server.telemetry")

TELEMETRY_CONFIG_FILE = "telemetry_config.json"
DEFAULT_TELEMETRY_CONFIG: dict[str, Any] = {
    "enabled": True,
    "langfuse": {"enabled": False, "host": "", "public_key": "", "secret_key": ""},
}


def load_telemetry_config(state: Any) -> dict[str, Any]:
    raw = state.load_json_config(TELEMETRY_CONFIG_FILE, DEFAULT_TELEMETRY_CONFIG)
    raw = raw if isinstance(raw, dict) else {}
    langfuse = raw.get("langfuse") if isinstance(raw.get("langfuse"), dict) else {}
    return {
        "enabled": raw.get("enabled", True) is not False,
        "langfuse": {
            "enabled": langfuse.get("enabled") is True,
            "host": str(langfuse.get("host") or ""),
            "public_key": str(langfuse.get("public_key") or ""),
            "secret_key": str(langfuse.get("secret_key") or ""),
        },
    }


def _score_previous_turn(store: TraceStore, trace: Trace) -> None:
    """Delayed signal: this turn's user message judges the thread's previous turn."""
    previous = store.previous_trace(trace.thread_id, trace.start_time)
    if previous is None or not trace.input:
        return
    score = followup_score(previous["trace_id"], trace.input)
    if score is not None:
        store.add_score(score)


def _export(config: dict[str, Any], trace: Trace) -> None:
    from vera_agent.telemetry.exporters.langfuse import export_trace

    # Network export must not delay the finish event; failures are logged, not raised.
    threading.Thread(target=export_trace, args=(config["langfuse"], trace), daemon=True).start()


def persist_trace(store: TraceStore, config: dict[str, Any], trace: Trace) -> None:
    score_finished_trace(trace)
    store.save_trace(trace)
    _score_previous_turn(store, trace)
    if config["langfuse"]["enabled"]:
        _export(config, trace)


def new_trace(ctx: Any, profile_id: str | None = None) -> Trace:
    request, session = ctx.request, ctx.session
    return Trace(
        thread_id=request.thread_id,
        project_id=session.project_id,
        session_role=session.role,
        task_type=classify_task_type(request.content or "", request.workflow_stage, session.role),
        profile_id=profile_id,
        input=str(request.content or "")[:4000],
        model=str(ctx.model_profile.get("name") or ""),
        metadata={
            "group_id": session.group_id,
            "workflow_stage": request.workflow_stage,
            "rule_trigger": request.rule_trigger,
            "attached_skills": list(request.attached_skills or []),
            "permission_mode": ctx.mode,
            "recalled_memory_ids": ctx.memory_recall.memory_ids if ctx.memory_recall else [],
            "memory_tokens": ctx.memory_recall.tokens if ctx.memory_recall else 0,
        },
    )


def attach_turn_tracer(ctx: Any, on_finish: list[Any] | None = None) -> TurnTracer | None:
    """Give ``ctx`` a tracer that saves to the local store; returns None when tracing is off."""
    if ctx.request.ephemeral:
        return None
    try:
        config = load_telemetry_config(ctx.state)
        if not config["enabled"]:
            return None
        store = TraceStore.for_state(ctx.state)
    except Exception:
        logger.exception("Trace store unavailable; this turn is not traced")
        return None
    callbacks = [lambda trace: persist_trace(store, config, trace), *(on_finish or [])]
    ctx.tracer = TurnTracer(new_trace(ctx), on_finish=callbacks)
    return ctx.tracer

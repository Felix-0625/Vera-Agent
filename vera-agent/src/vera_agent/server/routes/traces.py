"""Local trace routes: browse traces, read one trace tree, success rates, and user feedback scores.

Routes:
- GET /api/traces: newest traces (query: thread_id, project_id, days, below_score, limit)
- GET /api/traces/summary: per task type trace count, mean outcome and success rate (query: days)
- GET /api/traces/{trace_id}: one trace with its span tree and latest scores
- POST /api/traces/{trace_id}/feedback: record a user score (body: value 0..1, comment)
- GET /api/settings/telemetry, PUT /api/settings/telemetry: local tracing and optional Langfuse export

Traces are written by the chat stream (`telemetry/recorder.py`) into
`<projects_config_root>/.agents/traces.db`.
"""

from __future__ import annotations

import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.telemetry.recorder import TELEMETRY_CONFIG_FILE, load_telemetry_config
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Score


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _since(request: Request) -> float | None:
    try:
        days = float(request.query_params.get("days", "") or 0)
    except ValueError:
        return None
    return time.time() - days * 86400 if days > 0 else None


async def list_traces(request: Request) -> JSONResponse:
    params = request.query_params
    try:
        limit = int(params.get("limit", "50"))
        below_score = float(params["below_score"]) if params.get("below_score") else None
    except ValueError:
        return JSONResponse({"error": "limit and below_score must be numbers."}, status_code=400)
    traces = TraceStore.for_state(_get_state(request)).list_traces(
        thread_id=params.get("thread_id") or None,
        project_id=params.get("project_id") or None,
        since=_since(request),
        below_score=below_score,
        limit=limit,
    )
    return JSONResponse({"traces": traces})


async def trace_summary(request: Request) -> JSONResponse:
    summary = TraceStore.for_state(_get_state(request)).success_by_task_type(since=_since(request))
    return JSONResponse({"task_types": summary})


async def get_trace(request: Request) -> JSONResponse:
    trace = TraceStore.for_state(_get_state(request)).get_trace(request.path_params["trace_id"])
    if trace is None:
        return JSONResponse({"error": "Trace not found."}, status_code=404)
    return JSONResponse({"trace": trace})


async def add_trace_feedback(request: Request) -> JSONResponse:
    store = TraceStore.for_state(_get_state(request))
    trace_id = request.path_params["trace_id"]
    if store.get_trace(trace_id) is None:
        return JSONResponse({"error": "Trace not found."}, status_code=404)
    try:
        body = await request.json()
        value = float(body.get("value"))
    except (ValueError, TypeError):
        return JSONResponse({"error": "value must be a number from 0 to 1."}, status_code=400)
    if not 0.0 <= value <= 1.0:
        return JSONResponse({"error": "value must be a number from 0 to 1."}, status_code=400)
    score = Score(trace_id, "user_feedback", value, "user", str(body.get("comment") or "")[:500])
    store.add_score(score)
    return JSONResponse({"score": score.to_dict()}, status_code=201)


def _public_telemetry_config(config: dict) -> dict:
    """Never return the Langfuse secret key to the UI; report only whether one is saved."""
    langfuse = dict(config["langfuse"])
    langfuse["secret_key_set"] = bool(langfuse.pop("secret_key"))
    return {"enabled": config["enabled"], "langfuse": langfuse}


async def get_telemetry_settings(request: Request) -> JSONResponse:
    return JSONResponse(_public_telemetry_config(load_telemetry_config(_get_state(request))))


async def update_telemetry_settings(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Expected a JSON object."}, status_code=400)
    current = load_telemetry_config(state)
    if "enabled" in body:
        current["enabled"] = body["enabled"] is True
    langfuse_update = body.get("langfuse")
    if isinstance(langfuse_update, dict):
        for key in ("host", "public_key", "secret_key"):
            if isinstance(langfuse_update.get(key), str) and (key != "secret_key" or langfuse_update[key]):
                current["langfuse"][key] = langfuse_update[key].strip()
        if "enabled" in langfuse_update:
            current["langfuse"]["enabled"] = langfuse_update["enabled"] is True
    host = current["langfuse"]["host"]
    if host and not host.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        return JSONResponse({"error": "Langfuse host must use https (or http on localhost)."}, status_code=400)
    state.save_json_config(TELEMETRY_CONFIG_FILE, current)
    return JSONResponse(_public_telemetry_config(current))


trace_routes = [
    Route("/api/traces", list_traces, methods=["GET"]),
    Route("/api/traces/summary", trace_summary, methods=["GET"]),
    Route("/api/traces/{trace_id}", get_trace, methods=["GET"]),
    Route("/api/traces/{trace_id}/feedback", add_trace_feedback, methods=["POST"]),
    Route("/api/settings/telemetry", get_telemetry_settings, methods=["GET"]),
    Route("/api/settings/telemetry", update_telemetry_settings, methods=["PUT"]),
]

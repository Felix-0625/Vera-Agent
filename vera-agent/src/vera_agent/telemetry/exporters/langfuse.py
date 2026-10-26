"""Export a finished trace to a Langfuse server through its public ingestion API.

Disabled by default; enable it in `telemetry_config.json` with a host and a key pair. Sending a
trace publishes the turn's (already redacted) input, output and tool arguments to that server.
The exporter uses `requests` directly, so the `langfuse` SDK is not a dependency.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any

import requests

from vera_agent.telemetry.trace import Trace

logger = logging.getLogger("vera_server.telemetry")


def _iso(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()


def _event(event_type: str, body: dict[str, Any], timestamp: float) -> dict[str, Any]:
    return {"id": str(uuid.uuid4()), "type": event_type, "timestamp": _iso(timestamp), "body": body}


def build_ingestion_batch(trace: Trace) -> list[dict[str, Any]]:
    """Map a local trace to Langfuse ingestion events (trace, spans/generations, scores)."""
    batch = [
        _event(
            "trace-create",
            {
                "id": trace.trace_id,
                "name": trace.task_type,
                "sessionId": trace.thread_id,
                "input": trace.input,
                "output": trace.output,
                "timestamp": _iso(trace.start_time),
                "metadata": {**trace.metadata, "exit_status": trace.exit_status, "steps": trace.steps},
                "tags": [trace.session_role, trace.exit_status],
            },
            trace.start_time,
        )
    ]
    for span in trace.spans:
        body = {
            "id": span.span_id,
            "traceId": trace.trace_id,
            "parentObservationId": span.parent_id,
            "name": span.name,
            "startTime": _iso(span.start_time),
            "endTime": _iso(span.end_time),
            "input": span.input,
            "output": span.output,
            "metadata": span.metadata,
            "level": "ERROR" if span.status == "error" else "DEFAULT",
        }
        if span.kind == "model":
            body["model"] = span.name
            body["usage"] = {
                "input": span.metadata.get("prompt_tokens", 0),
                "output": span.metadata.get("completion_tokens", 0),
            }
        batch.append(_event("generation-create" if span.kind == "model" else "span-create", body, span.start_time))
    for score in trace.scores:
        body = {
            "id": score.score_id,
            "traceId": trace.trace_id,
            "name": score.name,
            "value": score.value,
            "comment": score.comment,
        }
        batch.append(_event("score-create", body, score.created_at))
    return batch


def export_trace(config: dict[str, Any], trace: Trace, timeout: float = 10.0) -> bool:
    host = str(config.get("host") or "").rstrip("/")
    if not (host and config.get("public_key") and config.get("secret_key")):
        logger.warning("Langfuse export is enabled but host or keys are missing")
        return False
    try:
        response = requests.post(
            f"{host}/api/public/ingestion",
            json={"batch": build_ingestion_batch(trace)},
            auth=(config["public_key"], config["secret_key"]),
            timeout=timeout,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        logger.warning("Langfuse export failed for %s: %s", trace.trace_id, error)
        return False

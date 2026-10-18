"""Context checkpoints (compaction) using the configured LiteLLM client.

The durable transcript stays intact. Only the model-facing projection replaces
older turns with the latest checkpoint and keeps the recent raw turns.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import litellm

from vera_agent.models import GLOBAL_MODEL_STATS
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger(__name__)
DEFAULT_RESERVE_TOKENS = 16_384
DEFAULT_KEEP_RECENT_TOKENS = 20_000


def _token_count(messages: list[dict[str, Any]], model_name: str) -> int:
    try:
        return int(litellm.token_counter(model=model_name, messages=messages))
    except Exception:
        return sum((len(str(message.get("content") or "")) + 3) // 4 for message in messages)


def _ensure_message_ids(session: ThreadSession) -> None:
    for message in session.messages:
        if not message.get("id"):
            message["id"] = f"msg_{uuid.uuid4().hex}"


def _latest_checkpoint(session: ThreadSession) -> dict[str, Any] | None:
    checkpoints = session.metadata.get("context_checkpoints", [])
    if not checkpoints:
        return None
    valid_ids = {message.get("id") for message in session.messages}
    return next(
        (checkpoint for checkpoint in reversed(checkpoints) if checkpoint.get("first_kept_message_id") in valid_ids),
        None,
    )


def context_projection(session: ThreadSession) -> list[dict[str, Any]]:
    """Build model history from the latest summary checkpoint and untouched tail."""
    _ensure_message_ids(session)
    checkpoint = _latest_checkpoint(session)
    if not checkpoint:
        return list(session.messages)

    boundary_id = checkpoint["first_kept_message_id"]
    boundary = next(i for i, message in enumerate(session.messages) if message.get("id") == boundary_id)
    systems = [message for message in session.messages[:boundary] if message.get("role") == "system"]
    anchor = {
        "role": "user",
        "content": f"[{checkpoint.get('checkpoint_label', 'Earlier context checkpoint')}]\n\n{checkpoint['summary']}",
        "extra": {"compaction": True, "timestamp": checkpoint.get("timestamp")},
    }
    return systems + [anchor] + [message for message in session.messages[boundary:] if message.get("role") != "system"]


def _summarization_prompt(previous_summary: str, messages: list[dict[str, Any]]) -> str:
    blocks = []
    for message in messages:
        if message.get("role") == "system":
            continue
        details = [
            f"[{message.get('role', 'unknown')}{':' + str(message['name']) if message.get('name') else ''}] {message.get('content') or ''}"
        ]
        calls = message.get("tool_calls") or []
        if calls:
            details.append("Tool calls: " + json.dumps(calls, ensure_ascii=False, default=str))
        if message.get("role") == "tool":
            details.append(f"Tool result for {message.get('tool_call_id') or 'unknown call'}")
        blocks.append("\n".join(details))
    transcript = "\n\n".join(blocks)
    return f"""Create a concise, factual context checkpoint so another model can continue this task.
Preserve the user's original goal, explicit constraints and decisions, verified facts, exact file paths and identifiers, completed work, unresolved work, and the next action. Retain names, numbers, dates, quoted facts, and list items exactly when they may answer a later question; keep answer-bearing source sentences close to verbatim. Distinguish facts from assumptions. Do not invent missing details. Keep the summary compact and useful for continuing the task.

<previous_checkpoint>
{previous_summary or "(none)"}
</previous_checkpoint>

<new_history>
{transcript}
</new_history>"""


def compact_session(
    session: ThreadSession,
    model_name: str,
    model_kwargs: dict[str, Any],
    context_window: int | None,
    *,
    reserve_tokens: int = DEFAULT_RESERVE_TOKENS,
    keep_recent_tokens: int = DEFAULT_KEEP_RECENT_TOKENS,
    force: bool = False,
    reason: str = "threshold",
) -> dict[str, Any] | None:
    """Summarize an old message range while preserving the complete transcript.

    The cut is always a user-turn boundary, so tool calls and their results stay
    together. The latest checkpoint is folded into the next one incrementally.
    """
    _ensure_message_ids(session)
    if not context_window or context_window <= 0:
        try:
            context_window = int(litellm.get_model_info(model_name).get("max_input_tokens") or 0)
        except Exception:
            context_window = 0
    if not context_window:
        return None

    projection = context_projection(session)
    before_tokens = _token_count(projection, model_name)
    threshold = max(1, context_window - min(reserve_tokens, context_window // 5))
    if not force and before_tokens <= threshold:
        return None
    if len(projection) < 3:
        return None

    checkpoint = _latest_checkpoint(session)
    previous_summary = str(checkpoint.get("summary", "")) if checkpoint else ""
    start_id = checkpoint.get("first_kept_message_id") if checkpoint else None
    start = (
        next((i for i, message in enumerate(session.messages) if message.get("id") == start_id), 0) if start_id else 0
    )
    source = [message for message in session.messages[start:] if message.get("role") != "system"]
    if not source:
        return None

    if keep_recent_tokens <= 0:
        user_indices = [i for i, message in enumerate(source) if message.get("role") == "user"]
        cut = user_indices[-1] if user_indices else len(source)
        if cut == 0 and len(source) > 1:
            cut = len(source)
    else:
        accumulated = 0
        cut = len(source)
        for index in range(len(source) - 1, -1, -1):
            accumulated += _token_count([source[index]], model_name)
            if accumulated >= keep_recent_tokens:
                cut = index
                break
        user_boundaries = [i for i, message in enumerate(source) if message.get("role") == "user" and i >= cut]
        if user_boundaries:
            cut = user_boundaries[0]
            # A single oversized older turn can cross the entire retention
            # budget while scanning backward. In that case the first eligible
            # boundary is index zero and would fold nothing; advance to the next
            # user turn so the oversized turn can be summarized as one unit.
            if cut == 0 and len(user_boundaries) > 1:
                cut = user_boundaries[1]
        else:
            user_indices = [i for i, message in enumerate(source) if message.get("role") == "user"]
            cut = user_indices[-1] if user_indices else len(source)

    folded = source[:cut]
    if not folded:
        return None
    # The full raw transcript remains available; only trim stale tool outputs in
    # the one-off summarization request to keep it within the same model window.
    folded = [dict(message) for message in folded]
    for message in folded:
        content = message.get("content")
        if message.get("role") == "tool" and isinstance(content, str) and len(content) > 12_000:
            message["content"] = content[:6_000] + "\n[older tool output clipped for checkpoint generation]"

    prompt = _summarization_prompt(previous_summary, folded)
    call_kwargs = dict(model_kwargs)
    try:
        model_output_limit = int(litellm.get_model_info(model_name).get("max_output_tokens") or 4096)
    except Exception:
        model_output_limit = 4096
    configured_output_limit = int(call_kwargs.get("max_tokens") or 4096)
    call_kwargs["max_tokens"] = min(max(2048, configured_output_limit), 4096, model_output_limit)

    summary = ""
    summary_prompt_tokens = 0
    summary_completion_tokens = 0
    summary_cost = 0.0
    summary_attempts = 0
    for attempt in range(2):
        response = litellm.completion(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You compact agent conversation history into accurate, actionable checkpoints.",
                },
                {"role": "user", "content": prompt},
            ],
            **call_kwargs,
        )
        summary_attempts += 1
        usage = response.usage.model_dump() if hasattr(response.usage, "model_dump") else dict(response.usage or {})
        summary_prompt_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        summary_completion_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        try:
            call_cost = float(litellm.cost_calculator.completion_cost(response, model=model_name))
        except Exception:
            logger.warning("Could not calculate context-summary cost for %s", model_name)
            call_cost = 0.0
        summary_cost += call_cost
        if call_cost > 0:
            GLOBAL_MODEL_STATS.add(call_cost)
            session.add_cost(call_cost)
        session.n_calls += 1
        summary = str(response.choices[0].message.content or "").strip()
        if summary:
            break
        if attempt == 0:
            logger.warning("Context summary was empty for %s; retrying once", model_name)
    if not summary:
        return None

    retained = source[cut:]
    first_kept_id = retained[0].get("id") if retained else None
    if first_kept_id is None:
        # A terminal message is not useful as a context boundary; keep the final
        # user turn raw when possible.
        last_user = next((message for message in reversed(source) if message.get("role") == "user"), None)
        if last_user is None:
            return None
        first_kept_id = last_user["id"]

    timestamp = time.time()
    event = {
        "kind": "压缩",
        "timestamp": timestamp,
        "before_tokens": before_tokens,
        "context_window": context_window,
        "folded_message_count": len(folded),
        "kept_message_count": len(retained),
        "reason": reason,
        "model": model_name,
        "summary_prompt_tokens": summary_prompt_tokens,
        "summary_completion_tokens": summary_completion_tokens,
        "summary_cost_usd": summary_cost,
        "summary_attempts": summary_attempts,
        "token_count_basis": "local tokenizer estimate; not provider usage",
    }
    checkpoint_record = {
        **event,
        "summary": summary,
        "first_kept_message_id": first_kept_id,
        "model": model_name,
        "checkpoint_label": "分组节点换血交接摘要" if reason == "manual_rebirth" else "上下文压缩摘要",
    }
    session.metadata.setdefault("context_checkpoints", []).append(checkpoint_record)
    session.metadata.setdefault("context_events", []).append(event)
    session.updated_at = timestamp
    after_tokens = _token_count(context_projection(session), model_name)
    event["after_tokens"] = after_tokens
    checkpoint_record["after_tokens"] = after_tokens
    logger.info("Compacted session %s from %s to %s tokens", session.thread_id, before_tokens, after_tokens)
    return event


def subagent_rebirth_if_needed(
    session: ThreadSession,
    model_name: str,
    context_window: int | None,
    *,
    model_kwargs: dict[str, Any] | None = None,
    min_compactions: int = 3,
    high_watermark: float = 0.70,
) -> dict[str, Any] | None:
    """Rotate a subagent's model-facing context after repeated ineffective compaction."""
    checkpoints = session.metadata.get("context_checkpoints", [])
    if not context_window or context_window <= 0 or len(checkpoints) < min_compactions:
        return None
    # Count before the rebirth adds its own checkpoint to the same list.
    prior_compactions = len(checkpoints)
    used = _token_count(context_projection(session), model_name)
    percent = used / context_window
    if percent < high_watermark:
        return None
    event = compact_session(
        session,
        model_name,
        model_kwargs or {},
        context_window,
        force=True,
        keep_recent_tokens=0,
        reason="subagent_rebirth",
    )
    if not event:
        return None
    timestamp = time.time()
    rebirth = {
        "kind": "换血",
        "timestamp": timestamp,
        "detail": f"累计压缩 {prior_compactions} 次后仍占窗口 {percent:.0%}；保留完整轨迹并以新检查点继续",
        "before_tokens": used,
        "after_tokens": event["after_tokens"],
    }
    session.metadata.setdefault("context_events", []).append(rebirth)
    return rebirth

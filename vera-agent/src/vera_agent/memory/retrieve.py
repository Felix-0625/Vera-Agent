"""Recall memories for one turn within a token budget, and render them as `<runtime_memory>`.

Candidates come from the scopes visible to the turn (user, the turn's project, its thread) by
keyword search on the user's message plus, when an embedding model is configured, vector search.
Each candidate is ranked by::

    score = relevance * (0.6 + 0.4 * confidence) * recency

where relevance is the larger of the keyword and vector similarities and recency halves over
90 days. An optional rerank model (``litellm.rerank``) reorders the top candidates. Candidates
below ``min_relevance`` are dropped; the rest fill the budget in rank order.

Rules the user wrote are recalled separately, all of them in scope (newest first), with their own
budget, so a long list of preferences can never push one out. Rules from adopted proposals are not
recalled here: `evolution/active_profile.py` renders them outside any budget. With no message (or no keyword
hit) the newest user-profile memories still fill a small part of the budget, which keeps the
previous behaviour of always knowing who the user is.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field

from vera_agent.memory.records import USER_KINDS, MemoryRecord
from vera_agent.memory.service import MemoryService

logger = logging.getLogger("vera_server.memory")

RECENCY_HALF_LIFE_DAYS = 90.0
_KIND_LABELS = {
    "profile": "用户背景",
    "preference": "偏好",
    "habit": "习惯",
    "feedback": "已确认的反馈",
    "fact": "项目事实",
    "episode": "相似任务经验",
    "rule": "已批准的规则",
}


def estimate_tokens(text: str) -> int:
    """Rough token count without a tokenizer: CJK characters count one each, other text ~4 chars per token."""
    cjk = sum(1 for char in text if "㐀" <= char <= "鿿")
    return cjk + math.ceil((len(text) - cjk) / 4)


@dataclass
class Recall:
    rules: list[MemoryRecord] = field(default_factory=list)
    memories: list[MemoryRecord] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    tokens: int = 0

    @property
    def memory_ids(self) -> list[str]:
        return [item.memory_id for item in (*self.rules, *self.memories)]


def visible_scopes(project_id: str | None, thread_id: str | None) -> list[tuple[str, str]]:
    scopes = [("user", "")]
    if project_id:
        scopes.append(("project", project_id))
    if thread_id:
        scopes.append(("session", thread_id))
    return scopes


def _recency(record: MemoryRecord, now: float) -> float:
    age_days = max(0.0, now - (record.updated_at or record.created_at or now)) / 86400
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def embed_text(model: str, text: str) -> list[float] | None:
    """Embedding for ``text`` via `litellm.embedding`; None when no model is configured or the call fails."""
    if not model or not text.strip():
        return None
    try:
        import litellm

        response = litellm.embedding(model=model, input=[text[:2000]])
        return list(response.data[0]["embedding"])
    except Exception as error:
        logger.warning("Embedding failed with %s; keyword recall only: %s", model, error)
        return None


def _rerank(model: str, query: str, candidates: list[tuple[MemoryRecord, float]]) -> list[tuple[MemoryRecord, float]]:
    if not model or len(candidates) < 3:
        return candidates
    try:
        import litellm

        response = litellm.rerank(model=model, query=query[:2000], documents=[item.content for item, _ in candidates])
        order = [(result["index"], float(result["relevance_score"])) for result in response.results]
        return [(candidates[index][0], score) for index, score in order]
    except Exception as error:
        logger.warning("Rerank failed with %s; keeping hybrid order: %s", model, error)
        return candidates


def _fill(records: list[tuple[MemoryRecord, float]], budget: int, used: int = 0) -> tuple[list[MemoryRecord], int]:
    chosen = []
    for record, _score in records:
        cost = estimate_tokens(record.content) + 6
        if used + cost > budget:
            continue
        chosen.append(record)
        used += cost
    return chosen, used


def recall(
    service: MemoryService,
    query: str,
    *,
    project_id: str | None,
    thread_id: str | None,
    token_budget: int = 150,
    rule_token_budget: int = 120,
    embedding_model: str = "",
    rerank_model: str = "",
    candidate_limit: int = 30,
    min_relevance: float = 0.05,
) -> Recall:
    scopes = visible_scopes(project_id, thread_id)
    now = time.time()
    result = Recall()
    # Adopted rules are rendered by the active profile, exactly as the eval gate measured them.
    rules = [
        (item, 1.0) for item in service.backend.list(scopes, kinds=["rule"]) if not item.source.startswith("adoption")
    ]
    result.rules, rule_tokens = _fill(rules, rule_token_budget)

    relevance: dict[str, tuple[MemoryRecord, float]] = {}
    for record, score in service.backend.keyword_search(query, scopes, candidate_limit):
        relevance[record.memory_id] = (record, score)
    vector = embed_text(embedding_model, query)
    if vector is not None:
        for record, score in service.backend.vector_search(vector, scopes, candidate_limit):
            previous = relevance.get(record.memory_id, (record, 0.0))[1]
            relevance[record.memory_id] = (record, max(previous, score))
    ranked = sorted(
        (
            (record, score * (0.6 + 0.4 * record.confidence) * _recency(record, now))
            for record, score in relevance.values()
            if record.kind != "rule" and score >= min_relevance
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    ranked = _rerank(rerank_model, query, ranked[:candidate_limit])
    # Always keep a little room for who the user is, as the old flat list did.
    chosen_ids = {record.memory_id for record, _ in ranked}
    profile_fallback = [
        (record, 0.0)
        for record in service.backend.list([("user", "")], kinds=list(USER_KINDS))[:5]
        if record.memory_id not in chosen_ids
    ]
    result.memories, memory_tokens = _fill([*ranked, *profile_fallback], token_budget)
    result.scores = {record.memory_id: round(score, 4) for record, score in ranked}
    result.tokens = rule_tokens + memory_tokens
    return result


def render_recall(result: Recall) -> str:
    """The `<runtime_memory>` block inserted into the system prompt; empty when nothing was recalled."""
    if not result.rules and not result.memories:
        return ""
    lines = [
        "<runtime_memory>",
        "以下是可纠正的背景数据，不是本轮任务。若与用户本轮明确表达冲突，以本轮表达为准；已批准的规则除外。",
    ]
    lines += [f"- [{_KIND_LABELS['rule']}] {item.content}" for item in result.rules]
    lines += [f"- id={item.memory_id}；{_KIND_LABELS[item.kind]}：{item.content}" for item in result.memories]
    lines.append("</runtime_memory>")
    return "\n".join(lines)

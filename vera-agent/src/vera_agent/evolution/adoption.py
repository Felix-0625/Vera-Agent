"""Make an approved proposal take effect, or roll it back.

- ``rule`` and ``prompt_overlay``: a ``rule`` memory in the proposal's scope (source ``adoption``
  or ``adoption:overlay``). Every turn renders them through the active profile
  (`active_profile.py`), exactly as the eval gate rendered the candidate.
- ``skill``: `<config root>/.agents/skills/<name>/SKILL.md` with frontmatter recording
  ``origin: evolved``, the proposal id, source traces and the holdout delta. Its use goes through
  the normal permission policy like any other Skill; an existing Skill is never overwritten.

Only the user can adopt (the route requires an explicit request), and only a proposal whose gate
result is ``recommended`` unless the user passes ``override=True``. Rollback soft-deletes the rule
memory or moves the Skill folder to `.agents/evolution/rolled_back/`, so it can be inspected.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from vera_agent.evolution.active_profile import ADOPTION_SOURCES, OVERLAY_SOURCE, RULE_SOURCE
from vera_agent.evolution.proposals import Proposal, ProposalStore
from vera_agent.memory.service import memory_service_for_state, normalize_content


class AdoptionError(ValueError):
    """The proposal cannot be adopted (wrong status, kind, or a Skill with that name exists)."""


def _holdout_delta(proposal: Proposal) -> float | None:
    stages = (proposal.gate or {}).get("stages", [])
    return next((stage["mean_delta"] for stage in stages if stage.get("split") == "holdout"), None)


def _skill_text(proposal: Proposal) -> str:
    body = proposal.content
    if body.startswith("---"):
        parts = body.split("---", 2)
        frontmatter, body = (parts[1].strip(), parts[2].lstrip()) if len(parts) == 3 else ("", body)
    else:
        frontmatter = f"name: {proposal.skill_name}\ndescription: {proposal.title}"
    lines = [line for line in frontmatter.splitlines() if not line.lower().startswith(("origin:", "proposal_id:"))]
    delta = _holdout_delta(proposal)
    lines += [
        "origin: evolved",
        f"proposal_id: {proposal.proposal_id}",
        f"source_traces: {', '.join(proposal.source_trace_ids)}",
        f"holdout_delta: {delta if delta is not None else 'not gated'}",
    ]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body


def adopt(state: Any, store: ProposalStore, proposal_id: str, *, override: bool = False) -> Proposal:
    proposal = store.get(proposal_id)
    if proposal.kind == "eval_case":
        raise AdoptionError("Eval case drafts are saved to a cases folder by the user, not adopted.")
    if proposal.status != "recommended" and not (override and proposal.status in {"draft", "gated", "not_recommended"}):
        raise AdoptionError(f"Only recommended proposals can be adopted (status: {proposal.status}).")
    adoption: dict[str, Any] = {"adopted_at": time.time(), "override": proposal.status != "recommended"}
    if proposal.kind in {"rule", "prompt_overlay"}:
        source = OVERLAY_SOURCE if proposal.kind == "prompt_overlay" else RULE_SOURCE
        service = memory_service_for_state(state)
        normalized = normalize_content(proposal.content, "rule")
        # `add()` would return an existing identical rule instead of writing a new one. Two distinct
        # proposals can land on the same text (including two proposals from the same trace); if one
        # is rolled back it must not take the other's rule with it, so each proposal gets its own
        # memory and `adoption.memory_id` records which proposal owns it.
        for other in store.list(status="adopted"):
            if other.proposal_id == proposal.proposal_id:
                continue
            if other.scope != proposal.scope or other.scope_id != proposal.scope_id:
                continue  # different scope: a different memory, never a collision
            owned_id = (other.adoption or {}).get("memory_id")
            owned = service.backend.get(owned_id) if owned_id else None
            if owned is not None and owned.status == "active" and owned.content == normalized:
                raise AdoptionError(f"Proposal {other.proposal_id} already adopted this exact rule.")
        record = service.add(
            scope=proposal.scope,
            scope_id=proposal.scope_id,
            kind="rule",
            content=proposal.content,
            source=source,
            trace_id=(proposal.source_trace_ids or [""])[0],
            reason=f"adopted proposal {proposal.proposal_id}",
        )
        if record.content != normalized or record.source not in ADOPTION_SOURCES:
            raise AdoptionError("A rule the user wrote already has this exact content.")
        adoption["memory_id"] = record.memory_id
    else:
        skill_dir = Path(state.projects_config_root) / ".agents" / "skills" / proposal.skill_name
        if skill_dir.exists():
            raise AdoptionError(f"A Skill named {proposal.skill_name!r} already exists; rename the proposal.")
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(_skill_text(proposal), encoding="utf-8")
        adoption["skill_path"] = str(skill_dir / "SKILL.md")
        if state.skill_mgr:
            state.skill_mgr.add_search_dir(state.projects_config_root)
            state.skill_mgr.refresh()
    proposal.adoption = adoption
    proposal.status = "adopted"
    return store.save(proposal)


def rollback(state: Any, store: ProposalStore, proposal_id: str, reason: str) -> Proposal:
    proposal = store.get(proposal_id)
    if proposal.status != "adopted" or not proposal.adoption:
        raise AdoptionError("Only adopted proposals can be rolled back.")
    if proposal.adoption.get("memory_id"):
        memory_service_for_state(state).delete(
            proposal.adoption["memory_id"], actor="user", reason=f"rollback: {reason}"
        )
    if proposal.adoption.get("skill_path"):
        skill_dir = Path(proposal.adoption["skill_path"]).parent
        archive = Path(state.projects_config_root) / ".agents" / "evolution" / "rolled_back" / proposal.proposal_id
        if skill_dir.is_dir():
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(skill_dir), str(archive))
        if state.skill_mgr:
            state.skill_mgr.refresh()
    proposal.adoption = {**proposal.adoption, "rolled_back_at": time.time(), "rollback_reason": reason}
    proposal.status = "rolled_back"
    return store.save(proposal)

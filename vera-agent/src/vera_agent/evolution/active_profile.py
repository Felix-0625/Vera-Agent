"""The adopted profile: what the desktop app runs with, built from adopted proposals.

The eval gate measures ``baseline + proposal`` rendered through `AgentProfile.prompt_slots`.
Production must render an adopted proposal the same way, or the gate measured a different prompt
than the one users get. So adopted rules and prompt overlays bypass the memory recall budget:
every turn applies the active profile with `apply_profile_to_prompt`, the function the eval
runner uses.

The active profile is derived on demand from ``rule`` memories written by adoption (source
``adoption`` for rules, ``adoption:overlay`` for prompt overlays) in the scopes visible to the
turn, so a rollback (soft delete) takes effect on the next turn with no second copy to keep in
sync. Adopted Skills are installed Skill folders and are attached like any other Skill.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from vera_agent.evals.profile import AgentProfile, apply_profile_to_prompt
from vera_agent.memory.retrieve import visible_scopes
from vera_agent.memory.service import memory_service_for_state

RULE_SOURCE = "adoption"
OVERLAY_SOURCE = "adoption:overlay"
ADOPTION_SOURCES = (RULE_SOURCE, OVERLAY_SOURCE)


def active_profile(state: Any, project_id: str | None, thread_id: str | None) -> AgentProfile:
    """Baseline plus every adopted rule and overlay visible to this turn, oldest first."""
    records = memory_service_for_state(state).backend.list(visible_scopes(project_id, thread_id), kinds=["rule"])
    adopted = sorted((item for item in records if item.source in ADOPTION_SOURCES), key=lambda item: item.created_at)
    return AgentProfile(
        profile_id="active",
        rules=[item.content for item in adopted if item.source == RULE_SOURCE],
        prompt_overlay="\n\n".join(item.content for item in adopted if item.source == OVERLAY_SOURCE),
        note="adopted proposals",
    )


def extend_with_active_profile(state: Any) -> Callable[[str, dict[str, str], Any], str]:
    """`prepare_turn` prompt extender for desktop turns; a memory failure never blocks a turn."""

    def extend(system_prompt: str, prompt_vars: dict[str, str], session: Any) -> str:
        try:
            profile = active_profile(state, session.project_id, session.thread_id)
        except Exception:
            logging.getLogger("vera_server.evolution").exception("Active profile unavailable; using baseline")
            return system_prompt
        return apply_profile_to_prompt(system_prompt, prompt_vars, profile)

    return extend

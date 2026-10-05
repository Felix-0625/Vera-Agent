"""Typed Handoff Tools for Phase 5 agent relay and control transfer.

Adheres to Pi-agent minimalism and PydanticAI handoff semantics:
- transfer_to_researcher: Hand off architecture exploration to Researcher
- transfer_to_reviewer: Hand off code verification to Reviewer
- transfer_to_main: Subagent handoff back to Main Implementer with validated payload
"""

from __future__ import annotations

import logging
from typing import Any

from vera_agent.models.contracts import HandoverPayload
from vera_agent.session.pipeline import HandoffPipeline
from vera_agent.session.thread import ThreadSession

logger = logging.getLogger(__name__)


def transfer_to_researcher_op(
    session: ThreadSession,
    pipeline: HandoffPipeline,
    task: str,
    scope: list[str] | None = None,
) -> tuple[ThreadSession, HandoverPayload]:
    """Execute typed handoff from current session to Researcher subagent."""
    notes = f"Exploration Scope: {', '.join(scope)}" if scope else ""
    new_session, payload = pipeline.execute_handoff(
        session=session,
        target_role="researcher",
        target_problem=task,
        extra_notes=notes,
    )
    return new_session, payload


def transfer_to_reviewer_op(
    session: ThreadSession,
    pipeline: HandoffPipeline,
    verification_focus: str = "Pre-merge diff audit and regression test execution",
) -> tuple[ThreadSession, HandoverPayload]:
    """Execute typed handoff from current session to Reviewer subagent."""
    new_session, payload = pipeline.execute_handoff(
        session=session,
        target_role="reviewer",
        target_problem=verification_focus,
        next_action="Run test suite and verify edge cases",
    )
    return new_session, payload


def transfer_to_main_op(
    session: ThreadSession,
    pipeline: HandoffPipeline,
    summary: str,
    key_findings: list[str],
    rejected_paths: list[str] | None = None,
    recommended_next_action: str = "Proceed with code modifications",
) -> tuple[ThreadSession, HandoverPayload]:
    """Execute typed handoff from subagent back to Main Implementer."""
    new_session, payload = pipeline.execute_handoff(
        session=session,
        target_role="main",
        target_problem=summary,
        key_findings=key_findings,
        rejected_paths=rejected_paths or [],
        next_action=recommended_next_action,
    )
    return new_session, payload

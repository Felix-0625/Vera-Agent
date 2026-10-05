"""Context auto-rebirth pipeline and watermark monitor for Phase 5.

Adheres to Pi-agent minimalism and eliminates long-context hallucination:
- WatermarkPolicy: Configurable thresholds (turns, chars, cost) for proactive context refresh.
- HandoffPipeline: Manages clean session rebirth and typed handoffs between agent nodes.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from minisweagent.models.contracts import HandoverPayload
from minisweagent.session.graph import GitFlowGraph
from minisweagent.session.thread import ThreadSession

logger = logging.getLogger(__name__)


@dataclass
class WatermarkPolicy:
    """Configurable thresholds that monitor context bloat and trigger auto-rebirth."""

    max_turns: int = 16
    max_chars: int = 120_000
    max_cost: float = 0.50

    def check(self, session: ThreadSession) -> tuple[bool, str]:
        """Evaluate if the session exceeds any watermark threshold.

        Returns:
            (is_breached, reason)
        """
        # 1. Turn count check
        n_messages = len(session.messages)
        if n_messages >= self.max_turns * 2:  # turns usually mean user-assistant pairs
            return True, f"Turn limit exceeded: {n_messages // 2} turns >= {self.max_turns}"

        # 2. Character length check
        total_chars = sum(len(str(m.get("content") or "")) for m in session.messages)
        if total_chars >= self.max_chars:
            return True, f"Context character volume exceeded: {total_chars} chars >= {self.max_chars}"

        # 3. Cost check
        if session.cost >= self.max_cost:
            return True, f"Session cost watermark exceeded: ${session.cost:.2f} >= ${self.max_cost:.2f}"

        return False, "Context within healthy limits"


class HandoffPipeline:
    """Orchestrates seamless context handover, session archiving, and auto-rebirth."""

    def __init__(
        self,
        policy: WatermarkPolicy | None = None,
        graph: GitFlowGraph | None = None,
        archive_dir: Path | str | None = None,
    ):
        self.policy = policy or WatermarkPolicy()
        self.graph = graph
        self.archive_dir = Path(archive_dir) if archive_dir else None
        if self.archive_dir:
            self.archive_dir.mkdir(parents=True, exist_ok=True)

    def extract_handover_payload(
        self,
        session: ThreadSession,
        target_role: str = "main",
        target_problem: str | None = None,
        key_findings: list[str] | None = None,
        rejected_paths: list[str] | None = None,
        next_action: str = "",
    ) -> HandoverPayload:
        """Deterministically extract a clean HandoverPayload from session and physical state."""
        # 1. Physical touched files
        touched = [item["path"] for item in session.get_touched_files()]

        # 2. Problem description from initial user turn
        if not target_problem:
            if len(session.messages) > 1 and session.messages[1].get("role") == "user":
                target_problem = str(session.messages[1].get("content") or "")[:500]
            else:
                target_problem = "Current task in progress"

        # 3. Key findings from last assistant turn
        findings = key_findings or []
        if not findings:
            last_text = session.get_last_assistant_text()
            if last_text:
                # Take the first 3 non-empty lines
                lines = [line.strip("- *# ") for line in last_text.splitlines() if line.strip()]
                findings = lines[:3]
            else:
                findings = ["Execution in progress"]

        return HandoverPayload(
            source_thread_id=session.thread_id,
            role=session.role,
            target_problem=target_problem.strip(),
            touched_files=touched,
            key_findings=findings,
            rejected_paths=rejected_paths or [],
            next_action=next_action.strip() or "Continue implementation based on verified findings",
        )

    def execute_handoff(
        self,
        session: ThreadSession,
        target_role: str,
        target_problem: str | None = None,
        key_findings: list[str] | None = None,
        rejected_paths: list[str] | None = None,
        next_action: str = "",
        extra_notes: str = "",
    ) -> tuple[ThreadSession, HandoverPayload]:
        """Execute a clean session rebirth with structured handover.

        Steps:
        1. Extract validated HandoverPayload;
        2. Archive current session snapshot to disk (if archive_dir configured);
        3. Create a clean derived ThreadSession;
        4. Inject formatted Handover Markdown into derived session;
        5. Update topology graph if registered.
        """
        # 1. Build typed payload
        payload = self.extract_handover_payload(
            session=session,
            target_role=target_role,
            target_problem=target_problem,
            key_findings=key_findings,
            rejected_paths=rejected_paths,
            next_action=next_action,
        )

        # 2. Archive old session
        if self.archive_dir:
            archive_path = self.archive_dir / f"{session.thread_id}_archived.json"
            session.save(archive_path)
            logger.info("Archived exhausted session %s to %s", session.thread_id, archive_path)

        # 3. Spawn derived session
        new_session = ThreadSession(
            role=target_role,
            parent_thread_id=session.thread_id,
            group_id=session.group_id,
            metadata={
                "parent_cost": session.cost,
                "parent_calls": session.n_calls,
                "rebirth_timestamp": time.time(),
            },
        )

        # 4. Inject clean handover anchor
        handover_md = payload.to_markdown()
        if extra_notes:
            handover_md += f"\n## 5. Extra Directives\n{extra_notes.strip()}\n"

        new_session.add_messages({
            "role": "user",
            "content": f"[SYSTEM HANDOVER ANCHOR: Pure state inherited from parent session {session.thread_id}]\n\n{handover_md}",
            "extra": {"inherited": True, "parent_thread_id": session.thread_id},
        })

        # 5. Graph registration
        if self.graph:
            self.graph.register_session(
                thread_id=new_session.thread_id,
                role=target_role,
                group_id=session.group_id,
                status="active",
            )
            self.graph.record_communication(
                session.thread_id,
                new_session.thread_id,
                label="rebirth_handoff",
            )

        return new_session, payload

    def auto_rebirth_if_needed(
        self,
        session: ThreadSession,
        extra_notes: str = "",
    ) -> tuple[bool, ThreadSession, str]:
        """Check watermark policy and execute auto-rebirth if thresholds are breached.

        Returns:
            (did_rebirth: bool, active_session: ThreadSession, reason: str)
        """
        breached, reason = self.policy.check(session)
        if not breached:
            return False, session, reason

        logger.info("Context watermark breached for %s: %s. Initiating auto-rebirth...", session.thread_id, reason)
        new_session, _ = self.execute_handoff(
            session=session,
            target_role=session.role,
            extra_notes=f"Auto-rebirth triggered: {reason}. {extra_notes}",
        )
        return True, new_session, reason

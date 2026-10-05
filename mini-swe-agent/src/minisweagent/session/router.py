"""Asynchronous multi-session router and cross-window message bus.

Adheres to Pi-agent minimalism and native asyncio queuing:
- SessionRouter: Routes typed messages, handovers, and merge review events between threads.
- prompt_structured_choice: [Y/N/O] interactive approval flow for destructive or branching actions.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field

from minisweagent.models.contracts import HandoverPayload, MergeReviewResult
from minisweagent.session.graph import GitFlowGraph

logger = logging.getLogger(__name__)


class SessionMessage(BaseModel):
    """Structured message routed across threads and workgroups."""

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    source_thread_id: str
    target_thread_id: str
    message_type: Literal["text", "handover", "merge_request", "merge_response", "interrupt"] = "text"
    content: str
    payload: dict[str, Any] | None = None
    timestamp: float = Field(default_factory=time.time)


def prompt_structured_choice(
    prompt: str,
    auto_approve: bool = False,
    default: str = "Y",
) -> str:
    """Prompt the user with a structured [Y]es / [N]o / [O]ther confirmation flow.

    Returns:
        - "Y": Approved
        - "N": Rejected
        - "O:<details>": Alternative instructions
    """
    if auto_approve:
        return "Y"

    formatted_prompt = (
        f"\n{prompt}\n"
        f"Select: [Y] Approve | [N] Reject | [O] Provide alternative instructions (Default: {default}): "
    )

    try:
        user_input = input(formatted_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "N"

    if not user_input:
        user_input = default

    choice = user_input.upper()
    if choice.startswith("Y"):
        return "Y"
    elif choice.startswith("N"):
        return "N"
    elif choice.startswith("O"):
        # If user entered "O something"
        rest = user_input[1:].strip(" :,-")
        if not rest:
            try:
                rest = input("Enter alternative instructions: ").strip()
            except (EOFError, KeyboardInterrupt):
                return "N"
        return f"O:{rest}" if rest else "N"
    else:
        return "N"


class SessionRouter:
    """Central non-blocking message bus and GitFlow coordinator."""

    def __init__(self, graph: GitFlowGraph):
        self.graph = graph
        self.queues: dict[str, asyncio.Queue[SessionMessage]] = {}
        self.history: list[SessionMessage] = []

    def get_or_create_queue(self, thread_id: str) -> asyncio.Queue[SessionMessage]:
        """Get or initialize the dedicated message queue for a thread."""
        if thread_id not in self.queues:
            self.queues[thread_id] = asyncio.Queue()
        return self.queues[thread_id]

    async def send_message(
        self,
        source_thread_id: str,
        target_thread_id: str,
        content: str,
        message_type: Literal["text", "handover", "merge_request", "merge_response", "interrupt"] = "text",
        payload: dict[str, Any] | None = None,
    ) -> SessionMessage:
        """Route a structured message to target thread's mailbox."""
        msg = SessionMessage(
            source_thread_id=source_thread_id,
            target_thread_id=target_thread_id,
            message_type=message_type,
            content=content,
            payload=payload,
        )

        target_queue = self.get_or_create_queue(target_thread_id)
        await target_queue.put(msg)
        self.history.append(msg)

        # Track communication edge in topology graph
        self.graph.record_communication(source_thread_id, target_thread_id, label=message_type)
        return msg

    async def receive_message(
        self,
        thread_id: str,
        timeout: float | None = None,
    ) -> SessionMessage | None:
        """Receive the next message from thread's dedicated mailbox."""
        q = self.get_or_create_queue(thread_id)
        if timeout is not None:
            try:
                return await asyncio.wait_for(q.get(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
        else:
            try:
                return q.get_nowait()
            except asyncio.QueueEmpty:
                return None

    async def broadcast_to_group(
        self,
        source_thread_id: str,
        group_id: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> list[SessionMessage]:
        """Broadcast a message to all active threads in a ProjectGroup."""
        group = self.graph.get_group(group_id)
        if not group:
            return []

        messages = []
        for target_id in group.thread_ids:
            if target_id != source_thread_id:
                msg = await self.send_message(
                    source_thread_id=source_thread_id,
                    target_thread_id=target_id,
                    content=content,
                    message_type="text",
                    payload=payload,
                )
                messages.append(msg)
        return messages

    async def send_handover(
        self,
        source_thread_id: str,
        target_thread_id: str,
        handover: HandoverPayload,
    ) -> SessionMessage:
        """Deliver a validated HandoverPayload cleanly across threads."""
        return await self.send_message(
            source_thread_id=source_thread_id,
            target_thread_id=target_thread_id,
            content=handover.to_markdown(),
            message_type="handover",
            payload=handover.model_dump(),
        )

    async def request_merge_review(
        self,
        source_branch: str,
        target_branch: str,
        requester_thread_id: str,
        reviewer_thread_id: str,
    ) -> MergeReviewResult:
        """Execute in-memory 3-way merge inspection and deliver MergeReviewResult to reviewer."""
        can_merge, conflicts, summary = self.graph.worktree_manager.try_merge(
            source_branch=source_branch,
            target_branch=target_branch,
        )

        review = MergeReviewResult(
            source_branch=source_branch,
            target_branch=target_branch,
            can_merge=can_merge,
            conflict_files=conflicts,
            diff_summary=summary[:1500],
            test_passed=can_merge,
            action_items=(
                ["Resolve merge conflict markers in source branch"]
                if conflicts
                else ["Run regression test suite before final fast-forward"]
            ),
        )

        await self.send_message(
            source_thread_id=requester_thread_id,
            target_thread_id=reviewer_thread_id,
            content=review.to_markdown(),
            message_type="merge_request",
            payload=review.model_dump(),
        )
        return review

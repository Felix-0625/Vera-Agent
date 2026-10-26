"""Turn control signals and injectable tool-approval policies.

`TurnControl` carries a turn's interrupt and pause signals. The desktop routes back it with the
shared `ServerState` dictionaries so `/api/chat/interrupt`, `/pause` and `/resume` keep working;
headless callers (the eval runner) use `TurnControl.standalone` and own the signals themselves.

An `ApprovalPolicy` answers an approval request with the router protocol from
`session/router.py`: "Y" approves, "N" rejects, "O:<text>" rejects with a correction.
`InteractiveApprovalPolicy` waits for the user's click; `AutoApprovalPolicy` decides from an
allowlist and never waits, so evaluation runs stay unattended.
"""

from __future__ import annotations

import asyncio
import fnmatch
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Protocol

APPROVAL_TIMEOUT_SECONDS = 300.0
_SHELL_COMPOSITION = re.compile(r"[;&|<>`\n\r]|\$\(")


@dataclass
class TurnControl:
    """Interrupt and pause signals for one running turn."""

    thread_id: str
    interruption_flags: dict[str, bool]
    paused_threads: set[str]
    pause_event: threading.Event

    @classmethod
    def from_state(cls, state: Any, thread_id: str, pause_event: threading.Event) -> TurnControl:
        return cls(thread_id, state.interruption_flags, state.paused_chat_threads, pause_event)

    @classmethod
    def standalone(cls, thread_id: str) -> TurnControl:
        pause_event = threading.Event()
        pause_event.set()
        return cls(thread_id, {}, set(), pause_event)

    @property
    def interrupted(self) -> bool:
        return bool(self.interruption_flags.get(self.thread_id, False))

    def interrupt(self) -> None:
        self.interruption_flags[self.thread_id] = True
        self.paused_threads.discard(self.thread_id)
        self.pause_event.set()

    async def wait_if_paused(self) -> None:
        # Keep the stream/session alive while pausing delivery. Model tokens may buffer in the
        # worker queue; tools and the next reasoning step remain gated until the user resumes.
        while self.thread_id in self.paused_threads and not self.interrupted:
            await asyncio.sleep(0.1)


class ApprovalPolicy(Protocol):
    """Decides whether a tool action that requires approval may run."""

    async def decide(self, *, thread_id: str, action_id: str, action: dict[str, Any], category: str) -> str: ...


class InteractiveApprovalPolicy:
    """Wait for `/api/chat/confirm`; a timeout or interruption rejects the action."""

    def __init__(self, pending_approvals: dict[str, asyncio.Future[str]], timeout: float = APPROVAL_TIMEOUT_SECONDS):
        self.pending_approvals = pending_approvals
        self.timeout = timeout

    async def decide(self, *, thread_id: str, action_id: str, action: dict[str, Any], category: str) -> str:
        future = asyncio.get_running_loop().create_future()
        pending_key = f"{thread_id}:{action_id}"
        self.pending_approvals[pending_key] = future
        try:
            return await asyncio.wait_for(future, timeout=self.timeout)
        except asyncio.TimeoutError:
            return "N"
        finally:
            self.pending_approvals.pop(pending_key, None)


@dataclass
class AutoApprovalPolicy:
    """Unattended approvals for evaluation sandboxes.

    File edits are approved because the environment's write boundary is the disposable sandbox.
    Terminal commands are approved only when they match ``command_allowlist`` (shell-style
    patterns); search, MCP and any other category are rejected unless listed in
    ``allowed_categories``. Every decision is kept in ``decisions`` for the trace.
    """

    command_allowlist: list[str] = field(default_factory=list)
    allowed_categories: set[str] = field(default_factory=lambda: {"read", "create", "edit"})
    decisions: list[dict[str, Any]] = field(default_factory=list)

    async def decide(self, *, thread_id: str, action_id: str, action: dict[str, Any], category: str) -> str:
        if category == "terminal":
            raw_command = str(action.get("command", ""))
            command = " ".join(raw_command.split())
            # A pattern such as "pytest*" must not also approve "pytest; curl ...": chaining,
            # pipes, redirection and substitution are never auto-approved.
            approved = not _SHELL_COMPOSITION.search(raw_command) and any(
                fnmatch.fnmatchcase(command, pattern) for pattern in self.command_allowlist
            )
        else:
            approved = category in self.allowed_categories
        choice = "Y" if approved else "N"
        self.decisions.append({"action_id": action_id, "category": category, "choice": choice})
        return choice

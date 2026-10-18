"""Typed contracts and dependency containers shared by the multi-agent session layer.

Adheres to Pi-agent minimalism and Pydantic validation:
- AgentDeps: Dependency container for execution contexts
- HandoverPayload: Structured, clean handover between agents/sessions
- MergeReviewResult: PR-like cross-branch merge inspection payload
- GraphTopology: React Flow-compatible node/edge data structures for visual GitFlow
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


@dataclass
class AgentDeps:
    """Runtime dependencies injected into Agent tools and execution contexts."""

    env: Any
    session: Any
    worktree_path: Path | None = None
    scratch_dir: Path | None = None
    group_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HandoverPayload(BaseModel):
    """Immutable structured handover payload between agent sessions or branches.

    Guarantees no memory contamination and enforces explicit negative constraints
    (rejected_paths) to eliminate goal drift.
    """

    source_thread_id: str
    role: str = "researcher"
    target_problem: str
    touched_files: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list, max_length=10)
    rejected_paths: list[str] = Field(
        default_factory=list,
        description="Explicitly rejected or abandoned paths to prevent resurrection.",
    )
    next_action: str = ""
    timestamp: float = Field(default_factory=time.time)

    def to_markdown(self) -> str:
        """Render a clean, token-efficient Markdown handover summary."""
        lines = [
            f"# Context Handover [{self.role.upper()} -> Next]",
            f"- **Source Thread**: `{self.source_thread_id}`",
            f"- **Target Problem**: {self.target_problem.strip()}",
            "",
            "## 1. Touched Files",
        ]
        if self.touched_files:
            for f in self.touched_files:
                lines.append(f"- `{f}`")
        else:
            lines.append("- *(No files modified)*")

        lines.extend(["", "## 2. Key Findings & Invariants"])
        if self.key_findings:
            for k in self.key_findings:
                lines.append(f"- {k}")
        else:
            lines.append("- *(None)*")

        if self.rejected_paths:
            lines.extend(["", "## 3. Rejected & Discarded Paths [DO NOT REPEAT]"])
            for r in self.rejected_paths:
                lines.append(f"- ❌ {r}")

        lines.extend(["", "## 4. Recommended Next Action", self.next_action.strip() or "- Proceed with implementation"])
        return "\n".join(lines) + "\n"


class MergeReviewResult(BaseModel):
    """Structured inspection report for cross-branch merge requests."""

    source_branch: str
    target_branch: str
    can_merge: bool
    conflict_files: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    test_passed: bool = True
    action_items: list[str] = Field(default_factory=list)
    reviewer_notes: str = ""
    timestamp: float = Field(default_factory=time.time)

    def to_markdown(self) -> str:
        status_icon = "✅ CAN MERGE" if self.can_merge and self.test_passed else "❌ MERGE BLOCKED"
        lines = [
            f"# Merge Review Report: `{self.source_branch}` -> `{self.target_branch}`",
            f"**Status**: {status_icon}",
            f"- **Automated Tests**: {'PASSED' if self.test_passed else 'FAILED'}",
            "",
            "## 1. Conflict Status",
        ]
        if self.conflict_files:
            lines.append(f"**Conflicts detected in {len(self.conflict_files)} files:**")
            for c in self.conflict_files:
                lines.append(f"- `[CONFLICT]` {c}")
        else:
            lines.append("- No merge conflicts detected.")

        if self.diff_summary:
            lines.extend(["", "## 2. Diff Summary", f"```\n{self.diff_summary.strip()}\n```"])

        if self.action_items:
            lines.extend(["", "## 3. Required Action Items"])
            for a in self.action_items:
                lines.append(f"- [ ] {a}")

        if self.reviewer_notes:
            lines.extend(["", "## 4. Reviewer Notes", self.reviewer_notes.strip()])

        return "\n".join(lines) + "\n"


class GraphNode(BaseModel):
    """React Flow standard node model."""

    id: str
    type: Literal["branchNode", "worktreeNode", "sessionNode"]
    data: dict[str, Any]
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})


class GraphEdge(BaseModel):
    """React Flow standard edge model."""

    id: str
    source: str
    target: str
    label: str | None = None
    animated: bool = False


class GraphTopology(BaseModel):
    """Complete React Flow-compatible topology state for Web frontend visualization."""

    graph_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time.time)

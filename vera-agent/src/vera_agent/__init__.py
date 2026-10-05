"""VeraAgent (vera-agent) - Minimalist Multi-Agent GitFlow Collaboration Engine.

Re-exports core APIs from minisweagent for clean namespace migration.
"""

from minisweagent import __version__
from minisweagent.agents.default import DefaultAgent
from minisweagent.agents.interactive import InteractiveAgent
from minisweagent.models.contracts import (
    AgentDeps,
    GraphTopology,
    HandoverPayload,
    MergeReviewResult,
)
from minisweagent.session.graph import GitFlowGraph, ProjectGroup
from minisweagent.session.pipeline import HandoffPipeline, WatermarkPolicy
from minisweagent.session.router import SessionMessage, SessionRouter, prompt_structured_choice
from minisweagent.session.thread import ThreadSession
from minisweagent.session.worktree import WorktreeManager

__all__ = [
    "__version__",
    "DefaultAgent",
    "InteractiveAgent",
    "ThreadSession",
    "WorktreeManager",
    "ProjectGroup",
    "GitFlowGraph",
    "SessionRouter",
    "SessionMessage",
    "HandoffPipeline",
    "WatermarkPolicy",
    "AgentDeps",
    "HandoverPayload",
    "MergeReviewResult",
    "GraphTopology",
    "prompt_structured_choice",
]

"""Core exports for the session management layer."""

from vera_agent.session.graph import GitFlowGraph, ProjectGroup
from vera_agent.session.pipeline import HandoffPipeline, WatermarkPolicy
from vera_agent.session.router import SessionMessage, SessionRouter, prompt_structured_choice
from vera_agent.session.thread import ThreadSession
from vera_agent.session.worktree import WorktreeManager

__all__ = [
    "ThreadSession",
    "WorktreeManager",
    "ProjectGroup",
    "GitFlowGraph",
    "SessionRouter",
    "SessionMessage",
    "prompt_structured_choice",
    "HandoffPipeline",
    "WatermarkPolicy",
]

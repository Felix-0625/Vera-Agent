"""VeraAgent ASGI application entry point and domain routing aggregator.

Adheres to Pi-agent minimalism and strict modular domain architecture:
- server/state.py: Global ServerState runtime context and workspace configuration
- server/routes/chat.py: SSE inference stream, human-in-the-loop approvals, interruption
- server/routes/projects.py: Multi-project binding and history management
- server/routes/threads.py: Threads search, lifecycle, and SideChat context probe
- server/routes/groups.py: GitFlow business groups, topologies, and explicit registry
- server/routes/files.py: File explorer tree, safe content preview, AST checking
- server/routes/worktrees.py: Git diff, file staging, discarding, and checkpointing
- server/routes/gitflow.py: Topology graph, branch operations, and 3-Way merge reviews
- server/routes/terminal.py: Sandboxed terminal command execution
- server/routes/tasks.py: One-time scheduled tasks CRUD and execution
- server/routes/settings.py: LLM configs, permissions whitelist, AGENTS.md rules
- server/routes/mcp.py: MCP Servers protocol bus and marketplace
- server/routes/skills.py: Skill ecosystem scanning, installation, and prompt templates
- server/routes/analytics.py: Token throughput, cost, and health metrics dashboard
- server/routes/sessions.py: Health check, worktree attachments, and message dispatch
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from vera_agent.server.routes.analytics import analytics_routes
from vera_agent.server.routes.chat import chat_routes
from vera_agent.server.routes.files import file_routes
from vera_agent.server.routes.gitflow import gitflow_routes
from vera_agent.server.routes.groups import group_routes
from vera_agent.server.routes.mcp import mcp_routes
from vera_agent.server.routes.projects import project_routes
from vera_agent.server.routes.sessions import session_routes
from vera_agent.server.routes.settings import settings_routes
from vera_agent.server.routes.skills import skill_routes
from vera_agent.server.routes.taskboard import taskboard_routes
from vera_agent.server.routes.tasks import start_scheduler, stop_scheduler, task_routes
from vera_agent.server.routes.terminal import terminal_routes
from vera_agent.server.routes.threads import thread_routes
from vera_agent.server.routes.worktrees import worktree_routes
from vera_agent.server.state import ServerState
from vera_agent.session.graph import GitFlowGraph

logger = logging.getLogger("vera_server")


def create_app(
    repo_root: Path | str | None = None,
    graph: GitFlowGraph | None = None,
) -> Starlette:
    """Factory creating the modular ASGI application for multi-agent Web control."""
    server_state = ServerState(repo_root=repo_root, graph=graph)

    routes: list[Route] = [
        *session_routes,
        *chat_routes,
        *project_routes,
        *thread_routes,
        *group_routes,
        *file_routes,
        *worktree_routes,
        *gitflow_routes,
        *terminal_routes,
        *task_routes,
        *taskboard_routes,
        *settings_routes,
        *mcp_routes,
        *skill_routes,
        *analytics_routes,
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    @asynccontextmanager
    async def lifespan(app: Starlette):
        start_scheduler(app)
        try:
            yield
        finally:
            await stop_scheduler(app)

    app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
    app.state.server_state = server_state
    return app

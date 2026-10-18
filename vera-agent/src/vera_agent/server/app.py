"""ASGI application factory for the VeraAgent local API.

`create_app` builds one `ServerState` and mounts every route list from
`server/routes/`. Route modules by domain:

- sessions.py: health check, session attach/detach, direct inter-session messages
- chat.py: SSE chat stream, tool approval, interrupt/pause/resume
- projects.py: project binding, folder picker, project history
- threads.py: conversation list/CRUD, message replay/truncation, context status
- groups.py: topology templates, workflow/architecture instances, runs, registry
- files.py: file tree, preview/raw content, saving, syntax check, symbol search
- worktrees.py: Git diff, stage/discard, checkpoint, reset
- gitflow.py: topology export, branch create/delete/checkout/merge, merge review
- terminal.py: one-shot command execution and an interactive PowerShell WebSocket
- tasks.py: one-time scheduled Agent prompts and the background scheduler
- taskboard.py: project task board work items (SQLite)
- settings.py: model profiles, permissions, rules, context settings, user memories
- mcp.py: MCP server registry and Registry market install
- skills.py: Skill discovery, enable/disable, market install
- analytics.py: usage dashboard derived from persisted conversation events

The API has no authentication and is meant to listen on loopback only. CORS is
currently open (`*`) so the Vite dev server and the desktop shell can call it.
See docs/API.md for the endpoint reference.
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

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
- traces.py: local turn traces, span trees, outcome scores, telemetry settings
- memories.py: scoped versioned memories, pending changes, version history
- evolution.py: improvement proposals, eval gate results, adoption and rollback

The API has no authentication and is meant to listen on loopback only. `security.py` refuses non-loopback
`Host` and `Origin` headers so a web page cannot drive it from the browser. The desktop window loads the
built UI from this same server (`frontend_dist`). See docs/API.md for the endpoint reference.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import BaseRoute, Mount
from starlette.staticfiles import StaticFiles

from vera_agent.server.routes.analytics import analytics_routes
from vera_agent.server.routes.chat import chat_routes
from vera_agent.server.routes.evolution import evolution_routes
from vera_agent.server.routes.files import file_routes
from vera_agent.server.routes.gitflow import gitflow_routes
from vera_agent.server.routes.groups import group_routes
from vera_agent.server.routes.mcp import mcp_routes
from vera_agent.server.routes.memories import memory_routes
from vera_agent.server.routes.projects import project_routes
from vera_agent.server.routes.sessions import session_routes
from vera_agent.server.routes.settings import settings_routes
from vera_agent.server.routes.skills import skill_routes
from vera_agent.server.routes.taskboard import taskboard_routes
from vera_agent.server.routes.tasks import start_scheduler, stop_scheduler, task_routes
from vera_agent.server.routes.terminal import terminal_routes
from vera_agent.server.routes.threads import thread_routes
from vera_agent.server.routes.traces import trace_routes
from vera_agent.server.routes.worktrees import worktree_routes
from vera_agent.server.security import security_middleware
from vera_agent.server.state import ServerState
from vera_agent.session.graph import GitFlowGraph

logger = logging.getLogger("vera_server")


def create_app(
    repo_root: Path | str | None = None,
    graph: GitFlowGraph | None = None,
    frontend_dist: Path | str | None = None,
) -> Starlette:
    """Factory creating the modular ASGI application for multi-agent Web control.

    ``frontend_dist`` is the built UI directory to serve at ``/``; leave it unset for API-only use (tests, Vite dev).
    """
    frontend_dist = Path(frontend_dist) if frontend_dist else None
    server_state = ServerState(repo_root=repo_root, graph=graph)

    routes: list[BaseRoute] = [
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
        *trace_routes,
        *memory_routes,
        *evolution_routes,
    ]

    # The built UI is served last so every /api route wins; same-origin hosting means the desktop window needs
    # no CORS and no absolute API address.
    if frontend_dist is not None and frontend_dist.is_dir():
        routes.append(Mount("/", app=StaticFiles(directory=frontend_dist, html=True)))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        start_scheduler(app)
        try:
            yield
        finally:
            await stop_scheduler(app)

    app = Starlette(routes=routes, middleware=security_middleware(), lifespan=lifespan)
    app.state.server_state = server_state
    return app

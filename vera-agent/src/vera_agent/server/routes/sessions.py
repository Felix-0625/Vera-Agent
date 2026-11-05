"""Health route.

Route: GET /api/health (lightweight liveness check for scripts and monitors).
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def health(request: Request) -> JSONResponse:
    state = _get_state(request)
    return JSONResponse({"status": "ok", "repo_root": str(state.root_path)})


session_routes = [
    Route("/api/health", health, methods=["GET"]),
]

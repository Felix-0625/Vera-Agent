"""Browser-facing protection for the local API.

The API has no login: anything that can reach it can run shell commands. It therefore binds to loopback and
refuses requests that a web page on another site could send to it:

- ``Host`` must be a loopback name (blocks DNS rebinding, where an attacker's domain resolves to 127.0.0.1).
- ``Origin``, when a browser sends one, must be a loopback origin (blocks cross-site form posts and fetches,
  including "simple" requests that skip the CORS preflight).

Requests without ``Origin`` (curl, tests, same-origin GETs) are allowed; they are not a cross-site attack.
"""

from __future__ import annotations

import re

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Read when the app is built, so tests can extend it with their ASGI test host names.
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
LOOPBACK_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")


class LoopbackOriginMiddleware:
    """Reject HTTP and WebSocket requests whose ``Origin`` header is not a loopback origin."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            origin = dict(scope["headers"]).get(b"origin")
            if origin is not None and not LOOPBACK_ORIGIN.match(origin.decode("latin-1")):
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 1008})
                else:
                    await PlainTextResponse("Cross-origin request refused", status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def security_middleware() -> list[Middleware]:
    """Host check, then Origin check, then CORS for the loopback origins (Vite dev server)."""
    return [
        Middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS)),
        Middleware(LoopbackOriginMiddleware),
        Middleware(
            CORSMiddleware,
            allow_origin_regex=LOOPBACK_ORIGIN.pattern,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ]

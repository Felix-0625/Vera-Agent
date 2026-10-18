"""Local Starlette API used by the VeraAgent desktop UI."""

from vera_agent.server.app import create_app

__all__ = ["create_app"]

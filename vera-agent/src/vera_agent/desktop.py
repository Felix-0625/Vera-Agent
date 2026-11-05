"""Run VeraAgent as a desktop app: a loopback API that also serves the built UI, shown in a WebView2 window.

The UI and the API share one origin, so the browser needs no CORS and the API can refuse every other origin
(see ``server/security.py``). ``VERA_AGENT_DESKTOP_URL`` points the window at a Vite dev server instead.
"""

import os
import socket
import threading
import time
from pathlib import Path

import uvicorn
import webview

from vera_agent.server.app import create_app

HOST = "127.0.0.1"
PORT_RANGE = range(8000, 8101)
STARTUP_TIMEOUT_SECONDS = 30


def find_free_port() -> int:
    """Return the first free loopback port from 8000, so a port taken by another program is skipped."""
    for port in PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex((HOST, port)) != 0:
                return port
    raise RuntimeError(f"No free port between {PORT_RANGE.start} and {PORT_RANGE.stop - 1}")


def start_server(frontend_dist: Path, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    """Start the API in a background thread and wait until it accepts requests."""
    server = uvicorn.Server(uvicorn.Config(create_app(frontend_dist=frontend_dist), host=HOST, port=port))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError(f"API server failed to start on port {port}")
        time.sleep(0.1)
    return server, thread


def main() -> None:
    """Build-check the UI bundle, start the local API, and show the window until it is closed."""
    project_root = Path(__file__).resolve().parents[3]
    frontend_dist = project_root / "frontend" / "dist"
    icon = project_root / "frontend" / "public" / "logo.ico"
    if not (frontend_dist / "index.html").is_file():
        raise FileNotFoundError(f"Desktop frontend not built: {frontend_dist}")
    if not icon.is_file():
        raise FileNotFoundError(f"Desktop application icon not found: {icon}")

    server, thread = start_server(frontend_dist, find_free_port())
    local_app_data = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    try:
        webview.create_window(
            "VeraAgent",
            os.getenv("VERA_AGENT_DESKTOP_URL", f"http://{HOST}:{server.config.port}/"),
            width=1440,
            height=900,
            min_size=(1080, 680),
            resizable=True,
            background_color="#0D0E12",
        )
        webview.start(
            gui="edgechromium",
            icon=str(icon),
            private_mode=False,
            storage_path=str(local_app_data / "VeraAgent" / "WebView2"),
        )
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()

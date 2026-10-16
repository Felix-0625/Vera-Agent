"""Open the VeraAgent frontend in a native Windows WebView2 window."""

import os
from pathlib import Path

import webview


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    index = project_root / "frontend" / "dist" / "index.html"
    icon = project_root / "frontend" / "public" / "logo.ico"
    if not index.is_file():
        raise FileNotFoundError(f"Desktop frontend not built: {index}")
    if not icon.is_file():
        raise FileNotFoundError(f"Desktop application icon not found: {icon}")
    local_app_data = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    webview_data = local_app_data / "VeraAgent" / "WebView2"
    webview.create_window(
        "VeraAgent",
        os.getenv("VERA_AGENT_DESKTOP_URL", index.as_uri()),
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
        storage_path=str(webview_data),
    )


if __name__ == "__main__":
    main()

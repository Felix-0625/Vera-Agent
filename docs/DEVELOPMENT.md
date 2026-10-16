# Development setup

## Prerequisites

- Windows 10/11 for the native desktop shell, Git, Python 3.10+, and Node.js 20+.
- Microsoft Edge WebView2 Runtime for pywebview’s Edge Chromium backend.
- uv 0.11.15 for installing the Python dependency lock reproducibly.

## Start from source

```powershell
cd frontend
npm ci
cd ..\vera-agent
uv sync --locked --extra desktop --extra dev
cd ..
./start-desktop.ps1
```

For browser-only UI work, run `npm run dev` in `frontend` and run Uvicorn from `vera-agent`; Vite proxies API requests to `127.0.0.1:8000` by default. `VITE_API_PROXY_TARGET` can override the proxy target for local development.

## Repository conventions

- Do not put state, sessions, logs, API keys, downloaded packages, or generated worktrees in tracked source directories.
- Preserve `frontend/package-lock.json`; use `npm ci` for deterministic frontend dependency installation.
- Keep backend requirements and optional extras in `vera-agent/pyproject.toml`.
- Run the checks listed in [Testing](TESTING.md), then report any skipped live-provider or external-service checks.

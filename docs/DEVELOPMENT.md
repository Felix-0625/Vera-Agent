# Development setup

## Prerequisites

- Windows 10/11 for the native desktop shell, Git, Python 3.10+, and Node.js 20+.
- Microsoft Edge WebView2 Runtime for pywebview's Edge Chromium backend.
- uv 0.11+ (CI pins 0.11.15) for installing the locked Python dependencies.

The backend and frontend also build and test on Linux/macOS (CI runs on Ubuntu);
only the pywebview desktop window and PowerShell terminal are Windows-specific.

## Start from source

```powershell
cd frontend
npm ci
cd ..\vera-agent
uv sync --locked --extra desktop --extra dev
cd ..
./start-desktop.ps1
```

## Browser-based UI development

Run the API and the Vite dev server in two terminals:

```powershell
cd vera-agent
uv run uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` (including the terminal WebSocket) to
`VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`). To use the desktop window with
hot reload, set `VERA_AGENT_DESKTOP_URL=http://localhost:5173` and run
`uv run python -m vera_agent.desktop` from `vera-agent/`.

Application data is written to `.agents/` in the API's working directory (here
`vera-agent/.agents/`); see [DATA_MODEL.md](DATA_MODEL.md).

## Where to change what

| Change | Files | Also update |
| --- | --- | --- |
| New or changed API route | `vera-agent/src/vera_agent/server/routes/<domain>.py` (+ module docstring) | `frontend/src/api`, `frontend/src/types`, test in `vera-agent/tests/server/`, then `python scripts/generate_api_index.py` |
| Persisted record shape | the owning route/session module | [DATA_MODEL.md](DATA_MODEL.md) |
| New agent tool | `vera-agent/src/vera_agent/tools/` and role tool sets in `tools/primitives.py` | permission category in `server/permissions.py` |
| Built-in topology template | `vera-agent/src/vera_agent/session/templates.py` | |
| New right-side tool panel | see [frontend/README.md](../frontend/README.md#adding-a-right-side-tool-tab) | |
| Environment variable | the reading module | [CONFIGURATION.md](CONFIGURATION.md) table and `.env.example` (a test enforces both) |
| Dependencies | `vera-agent/pyproject.toml` + `uv lock`; `frontend/package.json` + `npm install` | Commit `uv.lock` / `package-lock.json`; regenerate [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) |

## Repository conventions

- Do not put state, sessions, logs, API keys, downloaded packages, or generated worktrees in tracked directories. `.agents/` is ignored everywhere.
- Install with lockfiles only: `uv sync --locked` and `npm ci`.
- Line endings are normalized to LF by `.gitattributes` (PowerShell/batch files use CRLF in the working tree).
- Run [`tests/check-all.ps1`](../tests/check-all.ps1) before submitting; see [TESTING.md](TESTING.md).
- Code style and naming rules are in [CONTRIBUTING.md](../CONTRIBUTING.md).

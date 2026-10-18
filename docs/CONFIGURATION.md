# Configuration and local data

## Where settings live

| What | Where | How to change |
| --- | --- | --- |
| Model providers, API keys, permissions, MCP servers, Skills, rules | `.agents/` under the application data root (`<checkout>/vera-agent/.agents/` for the desktop launcher) | The desktop app's **设置** dialog |
| Project data (conversations, workflow instances, runs, scheduled tasks) | `<project>/.agents/` | The app; never edit while it is running |
| Python CLI compatibility settings | `.env` in `VERA_GLOBAL_CONFIG_DIR` (default `%LOCALAPPDATA%\vera-agent\vera-agent` via platformdirs) | Copy entries from [`.env.example`](../.env.example) |
| Build-time frontend settings | `VITE_*` environment variables when running npm | Shell environment |

The full file layout and record shapes are in [DATA_MODEL.md](DATA_MODEL.md).
Existing process environment variables take precedence over values in `.env`.

## Environment variables

None are required for the desktop app: model credentials are entered in the UI.
Legacy `MSWEA_*` names come from mini-swe-agent and are kept for compatibility;
where a `VERA_*` alias exists it takes precedence.

| Variable | Read by | Purpose | Default |
| --- | --- | --- | --- |
| `VERA_GLOBAL_CONFIG_DIR` | `vera_agent/__init__.py` | Directory containing the Python `.env` file (alias: `MSWEA_GLOBAL_CONFIG_DIR`) | platformdirs user config dir |
| `VERA_SILENT_STARTUP` | `vera_agent/__init__.py` | Suppress the startup banner (alias: `MSWEA_SILENT_STARTUP`) | unset |
| `VERA_AGENT_BASH_PATH` | `environments/local.py` | Path to Git for Windows `bash.exe` for the local command tool | auto-detected |
| `VERA_AGENT_DESKTOP_URL` | `desktop.py` | URL loaded by the desktop window instead of `frontend/dist/index.html` (e.g. the Vite dev server) | built frontend |
| `VERA_MINI_CONFIG_PATH` | `run/mini.py` | YAML config for the inherited single-agent CLI (alias: `MSWEA_MINI_CONFIG_PATH`) | built-in `mini.yaml` |
| `VERA_RUN_NETWORK_TESTS` | backend tests | Set to `1` to run tests that call public web services | unset |
| `MSWEA_MODEL_NAME` | `models/__init__.py` | Default model for the Python CLI/adapters when none is given | unset |
| `OPENROUTER_API_KEY` | OpenRouter adapters | OpenRouter key (Python adapters only) | unset |
| `PORTKEY_API_KEY` | Portkey adapters | Portkey gateway key | unset |
| `PORTKEY_VIRTUAL_KEY` | Portkey adapters | Portkey virtual key | unset |
| `REQUESTY_API_KEY` | Requesty adapter | Requesty key | unset |
| `TAVILY_API_KEY` | `tools/web_tools.py` | Use Tavily for `web_search`; otherwise DuckDuckGo is used | unset |
| `LITELLM_MODEL_REGISTRY_PATH` | LiteLLM adapters | JSON registry with custom model cost/context metadata | unset |
| `MSWEA_COST_TRACKING` | model adapters | `default` (fail on missing cost data) or `ignore_errors` | `default` |
| `MSWEA_GLOBAL_COST_LIMIT` | `models/__init__.py` | Process-wide cost limit in USD; `0` disables | `0` |
| `MSWEA_GLOBAL_CALL_LIMIT` | `models/__init__.py` | Process-wide model call limit; `0` disables | `0` |
| `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT` | `models/utils/retry.py` | Maximum attempts per model request | `10` |
| `VITE_API_BASE_URL` | `frontend/vite.config.ts` | API origin compiled into the UI; set by `start-desktop.ps1` | dev: same origin; desktop: `http://127.0.0.1:8000` |
| `VITE_API_PROXY_TARGET` | `frontend/vite.config.ts` | Backend address for the `npm run dev` proxy | `http://127.0.0.1:8000` |

Provider keys such as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DEEPSEEK_API_KEY` are
read by LiteLLM only when you use the Python CLI with that provider; the desktop app
passes the key from its model settings instead. Benchmark-only variables of the
inherited mini-swe-agent environments (`MSWEA_DOCKER_EXECUTABLE`,
`MSWEA_SINGULARITY_EXECUTABLE`, `MSWEA_BUBBLEWRAP_EXECUTABLE`, `MSWEA_CONFIG_DIR`)
are documented in the upstream mini-swe-agent docs and are not used by the desktop app.

## Credentials

- Model API keys entered in the app are stored **unencrypted** in `models_config.json`
  under the application `.agents/` folder. API responses never return them.
- MCP server `env` and `headers` values may contain secrets and are stored in `mcp_servers.json`.
- Never commit `.env`, `.agents/`, provider keys, or exported conversations.
  `.env.example` contains only empty values and non-secret defaults.

## Project binding

Binding a folder records its path; it does not copy or sandbox the project. The
"project only" operation scope is an application path policy. Terminal and shell tools
run with your Windows account's permissions.

## Backups and updates

Close VeraAgent before copying `.agents/` folders. Git updates keep ignored `.agents/`
content, but nothing is backed up or synced automatically. After pulling changes,
rerun `npm ci` and `uv sync --locked --no-dev --extra desktop` if lockfiles changed.

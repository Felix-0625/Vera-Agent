# Environment variables

The desktop app has **no required environment variables**; enter model credentials in Settings. These variables are for startup, development, the Python CLI, tools, or tests. Process variables override Python `.env` values. When both legacy `MSWEA_*` and newer `VERA_*` aliases exist, the `VERA_*` name takes precedence.

| Variable | Used by | Purpose | Default |
| --- | --- | --- | --- |
| `VERA_GLOBAL_CONFIG_DIR` | Python startup | CLI `.env` directory; alias for `MSWEA_GLOBAL_CONFIG_DIR` | Platform user config directory |
| `VERA_SILENT_STARTUP` | Python startup | Hide startup banner; alias for `MSWEA_SILENT_STARTUP` | Unset |
| `VERA_AGENT_BASH_PATH` | Local command tool | Git for Windows `bash.exe` path | Auto-detect |
| `VERA_AGENT_DESKTOP_URL` | Desktop window | Load a specified frontend URL | Built frontend |
| `VERA_MINI_CONFIG_PATH` | Inherited CLI | YAML config; alias for `MSWEA_MINI_CONFIG_PATH` | Built-in `mini.yaml` |
| `VERA_RUN_NETWORK_TESTS` | Backend tests | Run public-network tests when `1` | Unset |
| `MSWEA_MODEL_NAME` | Python model adapter | Default CLI model | Unset |
| `OPENROUTER_API_KEY` | OpenRouter adapter | CLI adapter key | Unset |
| `PORTKEY_API_KEY` | Portkey adapter | Gateway key | Unset |
| `PORTKEY_VIRTUAL_KEY` | Portkey adapter | Virtual key | Unset |
| `REQUESTY_API_KEY` | Requesty adapter | Requesty key | Unset |
| `TAVILY_API_KEY` | Web search tool | Use Tavily; otherwise DuckDuckGo | Unset |
| `LITELLM_MODEL_REGISTRY_PATH` | LiteLLM adapter | Custom model cost/context metadata JSON | Unset |
| `MSWEA_COST_TRACKING` | Model adapter | `default` or `ignore_errors` | `default` |
| `MSWEA_GLOBAL_COST_LIMIT` | Model adapter | Process-wide USD cost cap; `0` disables | `0` |
| `MSWEA_GLOBAL_CALL_LIMIT` | Model adapter | Process-wide model-call cap; `0` disables | `0` |
| `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT` | Model retry | Maximum attempts per request | `10` |
| `VITE_API_BASE_URL` | Frontend build | API address embedded in UI | Same origin in dev; desktop defaults to `http://127.0.0.1:8000` |
| `VITE_API_PROXY_TARGET` | Vite dev server | `/api` proxy target for `npm run dev` | `http://127.0.0.1:8000` |

Provider variables such as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `DEEPSEEK_API_KEY` are read only by corresponding Python CLI/LiteLLM adapters. The desktop app gets keys from model Settings. Do not put real keys in source code, the website, screenshots, or shared `.env` files. See the repository [configuration reference](../../../../docs/CONFIGURATION.md#environment-variables).

## CLI setup-wizard variables only

These variables affect the inherited `mini-extra config` CLI wizard, **not** desktop startup or runtime:

| Variable | Purpose | Default |
| --- | --- | --- |
| `MSWEA_CONFIGURED` | Skip first-run `config setup` when already configured | Unset |
| `EDITOR` | Editor for `mini-extra config edit` | `nano` |

Benchmark-specific executor variables such as `MSWEA_DOCKER_EXECUTABLE`, `MSWEA_SINGULARITY_EXECUTABLE`, `MSWEA_BUBBLEWRAP_EXECUTABLE`, and `MSWEA_CONFIG_DIR` are likewise not used by the desktop app.

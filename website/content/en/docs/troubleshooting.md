# Troubleshooting and limitations

## Startup and connection

| Symptom | Check first |
| --- | --- |
| Backend Python environment missing | Run `uv sync --locked --no-dev --extra desktop` in `vera-agent/` |
| Desktop-window dependency missing | Install the `desktop` extra and WebView2 Runtime |
| Local API never becomes ready | Read `%TEMP%\vera-agent-desktop-backend-error.log`; check the selected port |
| Terminal tool cannot find Bash | Install Git for Windows or set `VERA_AGENT_BASH_PATH` to `bash.exe` |
| Model does not answer | Check model Settings, provider URL, key, and network; do not paste keys into issues |
| Dev frontend cannot reach API | Match `VITE_API_PROXY_TARGET` to the local backend port |

## Workflows and data

| Symptom | Meaning and action |
| --- | --- |
| Template looks correct but produces no result | A template is a definition. Create a project instance, start a run from a chat, and inspect node status and final delivery. |
| Run stops after refresh | Scheduling lives in the UI. Inspect `.agents/runs/`; there is currently no resume endpoint. |
| Task is linked to a chat but its status does not change | Linking is not acceptance. Review the result and update the task explicitly. |
| Threads are missing after migration | Back up and restore both application and project `.agents/` while the app is closed. |

## Current boundaries

- Installation is from GitHub source; there is no signed installer, auto-update, or uninstaller.
- The local API is designed for one user and has no public-service caller authentication.
- Path limits are application policy. Terminal commands have the current Windows user's permissions.
- Workflows run serially and are scheduled by the UI. Editor node names do not imply executors exist.
- Model, MCP, and Skill behavior depends on user configuration and external services. Interface illustrations on the introduction page are not real execution results.

When reporting a problem, include reproduction steps, version, nonsensitive errors, and relevant node/API status. **Do not** attach API keys, full conversation exports, or credential files from `.agents/`. See the repository [testing guide](../../../../docs/TESTING.md).

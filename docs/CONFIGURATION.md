# Configuration and local data

VeraAgent currently has more than one configuration location. The Python package uses `platformdirs` for its global `.env` file; the server also stores application/project registries and conversation-related state under `.agents` roots. Exact path selection depends on how the backend is launched and the route being used.

The project task board uses a local SQLite database at `<projects_config_root>/.agents/taskboard.sqlite`. This database is application-local, ignored by Git with the rest of `.agents`, and contains work-item records scoped by project ID. It is not synced between machines. Back it up with the installation's application data if the task board history matters.

The documented Windows source setup keeps the checkout wherever the user clones it; `.agents` runtime files remain in the app's configured data roots. Back up this data before manually moving or deleting it.

## Credentials

- Configure desktop model providers and credentials under **Settings → Models**. The form stores the selected model profile in VeraAgent application data.
- The Python package loads its compatibility `.env` from `VERA_GLOBAL_CONFIG_DIR` when set, otherwise from `platformdirs.user_config_dir("vera-agent")`. On Windows, the current default resolves to `%LOCALAPPDATA%\vera-agent\vera-agent`. Existing process environment variables take precedence over values loaded from the file.
- The repository [`.env.example`](../.env.example) covers legacy Python model adapters, optional Tavily search, custom LiteLLM registry metadata, cost tracking, and global model limits. The root [README environment table](../README.md#环境变量) explains each entry and its default.
- On Windows, `VERA_AGENT_BASH_PATH` can point to a specific Git for Windows `bash.exe` when automatic discovery cannot find it.
- Never commit `.env`, provider keys, MCP environment values, or session dumps.
- The `.env.example` template contains blank credential values and non-secret defaults; it must not contain usable secrets.
- Treat prompts, tool arguments, logs, and exported conversations as potentially sensitive.

## Project binding

Binding a folder records a local project path. It does not copy or sandbox the project. File-operation scope checks and terminal command permissions are separate controls. The user’s Windows account remains the OS identity used for local commands.

## Backups and updates

Keep a backup before replacing or updating a source checkout. Git updates can preserve ignored `.agents` content, but that data is not automatically backed up or synced. Close VeraAgent and verify the checkout is clean before updating it.

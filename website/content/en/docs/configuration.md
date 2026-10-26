# Configuration and local data

Configure the desktop app mainly through **Settings**. Environment variables primarily support startup, development, and the Python CLI; see [Environment variables](environment-variables.md).

## Models and credentials

In **Settings → Models**, add the provider, model name, endpoint, and API key; then choose a default model. Adjust context window, output limit, sampling, and tool-call limits as supported by the model. Keys are stored **unencrypted** in the application-level `.agents/models_config.json`. API responses omit the keys. Do not commit or share this file.

## Projects and threads

Binding a project stores its local path. Threads, organization/workflow instances, runs, and scheduled tasks are stored in the project's `.agents/`. Binding does not copy the project or limit terminal commands to its directory. Project files and Git state stay where they are.

## Permissions

Settings cover the default permission mode, action categories requiring approval, operation scope, and tool retry count. Categories include read, create, edit, terminal, search, MCP, and delegation. Server-side checks decide whether an action may run. “Project only” is an application-level path policy, **not a Windows sandbox**. Terminal commands run as the current user.

## MCP and Skills

MCP servers and Skill installation/toggles are application-level settings. An MCP server may launch a process or connect to the network. A Skill is an instruction package that can affect agent behavior. Marketplace listings are discovery aids, not signatures, security reviews, or project isolation. Inspect the source, commands, scripts, environment, and network access first.

## Data locations and backup

| Data | Desktop location | Examples |
| --- | --- | --- |
| Application `.agents/` | `<checkout>/vera-agent/.agents/` | Models, permissions, MCP/Skills, templates, task board |
| Project `.agents/` | `<project>/.agents/` | Threads, instances, runs, scheduled tasks |
| WebView2 data | `%LOCALAPPDATA%\VeraAgent\WebView2` | Desktop browser data |
| CLI `.env` | `VERA_GLOBAL_CONFIG_DIR`, default platform user config dir | Python CLI settings |

Task-board items live in application-level `taskboard.sqlite` and refer to projects by `project_id`. There is no automatic cloud sync. **Close VeraAgent before backing up**, then copy the relevant `.agents/` directories. See the [data model](../../../../docs/DATA_MODEL.md).

## Learning settings and backup

Application `.agents/` adds `traces.db`, `memory.db`, `telemetry_config.json`, `memory_config.json`, `evolution_config.json`, `evals/`, and `evolution/`. Databases include conversation excerpts, tool arguments, scoped memory, and history. Include them in backups and review redaction before sharing.

Local tracing is on by default; Langfuse export, Mem0, and model consolidation are off. Default recall budgets are 150 tokens plus 120 for user rules; adopted rules apply independently. The gate defaults to three repetitions per case/profile. See [Learning loop](../../../../docs/LEARNING_LOOP.md) for settings and costs.

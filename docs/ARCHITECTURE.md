# Architecture

## Runtime shape

The Windows desktop client is a local composition of three parts:

```text
React + TypeScript UI (Vite build)
          │ HTTP / WebSocket on loopback
          ▼
Python Starlette API (Uvicorn, 127.0.0.1:8000)
          │
          ├── ServerState: active project, sessions, registries, permissions
          ├── Agent/model loop: message history, model request, tool result
          └── local project files, Git, terminal, MCP and Skill adapters
```

`start-desktop.ps1` builds the UI, starts the local API when port 8000 is free, checks `/api/topology`, and opens `vera_agent.desktop` through pywebview/WebView2. In development the Vite server proxies `/api` to the local backend. The API is not a hosted multi-tenant service.

## Request and tool cycle

The chat route receives the selected thread/project and model configuration, appends the user turn, calls the configured model, executes returned tool actions through registered handlers, and returns streamed events to the UI. The persisted conversation and event records are the observable execution evidence. Internal model reasoning is not a supported trace contract and should not be represented as an execution log.

The implementation has multiple layers of state: process-local active objects in `ServerState`, project/application configuration in `.agents`, and project files/Git state in the selected workspace. Restart behavior and project ownership must be checked against the specific route; not every in-memory object is a durable database record.

## Project and application scope

- Projects are selected by local path and recorded in project history.
- Project files, sessions, rules, runs, and worktrees are associated with the project paths and `.agents` data described by the relevant routes.
- MCP/Skill installation and configuration are application-level, as accepted during the settings review; they are not isolated per project by the current product contract.
- The local path boundary is application policy. It is not an OS sandbox: terminal subprocesses run as the current Windows user and can access anything that user can access.

## Workflow and architecture instances

The UI exposes global templates and project-owned instances. A saved template is a definition, not proof that a workflow runner ran. Runtime acceptance requires a run record, node-level status, input/output provenance, and a surfaced final result. Consult the current implementation and tests before claiming every editor feature is executable; see [testing and limitations](TESTING.md).

## Trust boundaries

1. **Model provider:** user-configured remote service; prompts and selected project context may be sent to it.
2. **Local tools:** file, shell, Git, MCP and Skill actions can affect the local machine or project according to their implementation and permissions.
3. **External MCP/Skill packages:** repository metadata is not a security guarantee. Inspect code, command paths, environment variables, and network access before enabling.
4. **Loopback API:** binds to local machine in the desktop launcher. Keep it on loopback unless authentication and network exposure are deliberately designed.

This is an implementation overview, not a security certification or claim of operating-system isolation.

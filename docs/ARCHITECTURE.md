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

## Module map

Backend package `vera-agent/src/vera_agent/`:

| Path | Responsibility |
| --- | --- |
| `server/app.py` | `create_app` factory; mounts all route modules and the scheduler lifespan |
| `server/state.py` | `ServerState`: storage roots, JSON config helpers, in-memory sessions and approval flags |
| `server/routes/*.py` | One module per API domain; each module docstring lists its routes ([API.md](API.md)) |
| `server/routes/groups.py`, `runs.py`, `templates.py`, `group_store.py` | Groups and instances; run state validation; topology templates; shared persistence helpers |
| `server/chat/` | One chat turn: `turn_setup.py` (`prepare_turn` → `TurnContext`), `turn.py` (`run_turn`, the single execution path), `model_step.py` (compaction, history, model call), `actions.py` (tool execution and approvals), `control.py` (`TurnControl`, `ApprovalPolicy`), `request.py` (validation), `prompt.py` (system prompt), `mcp_session.py`, `subagents.py` |
| `telemetry/` | Traces, spans and outcome scores in `.agents/traces.db`; optional Langfuse export ([LEARNING_LOOP.md](LEARNING_LOOP.md)) |
| `memory/` | Scoped, versioned long-term memory with budgeted recall and Mem0-style consolidation |
| `evals/` | Eval cases, profiles, sandboxes, the headless runner over `run_turn`, comparisons, `vera-eval` CLI |
| `evolution/` | Critic proposals, the train/holdout/guard gate, adoption, the active profile every turn renders, online monitor and rollback |
| `server/permissions.py` | Permission policy: modes, categories, safe-command detection |
| `server/model_profile.py` | Resolves the model profile used by chat and context inspection |
| `server/user_context.py` | User rules, context settings, and the legacy user-memory API on top of `memory/` |
| `agents/default.py` | `DefaultAgent` loop inherited from mini-swe-agent: query model → parse actions → execute → observe |
| `models/` | Model adapters (LiteLLM, OpenRouter, Portkey, Requesty) and tool-call parsing (`models/utils/`) |
| `environments/` | Command execution backends; the desktop uses `local.py` (Git Bash on Windows) |
| `tools/` | Tool schemas and executors: file primitives, subagents, web search/fetch, handoff, Skills, code intelligence |
| `session/thread.py` | `ThreadSession`: one persisted conversation |
| `session/context_management.py` | Conversation compaction (checkpoints) |
| `session/templates.py` | Built-in topology templates |
| `session/graph.py`, `router.py`, `registry.py`, `pipeline.py`, `worktree.py` | Group graph, inter-session messages, agent registry, context rebirth, Git worktrees |
| `desktop.py` | pywebview window loading `frontend/dist` |
| `run/`, `config/` | Inherited mini-swe-agent CLI and benchmark runners (`vera`, `mini-extra`); not used by the desktop app |

Frontend: see [frontend/README.md](../frontend/README.md) for the `src/` map and stores.

## Request and tool cycle

The chat route validates the request and builds a `TurnContext` (session, working directory, permission policy, model, system prompt with recalled memories), then forwards the events of `run_turn`: append the user turn, call the model, execute returned tool actions through registered handlers and the injected `ApprovalPolicy`, repeat until the model stops or the tool budget runs out, persist the session. The eval runner drives the same `run_turn` with an automatic approval policy in a sandbox. The persisted conversation, event records and the local trace (spans and scores) are the observable execution evidence. Internal model reasoning is not a supported trace contract and should not be represented as an execution log.

Traces, scoring, memory, evals and the proposal loop are described in [LEARNING_LOOP.md](LEARNING_LOOP.md).

The implementation has multiple layers of state: process-local active objects in `ServerState`, project/application configuration in `.agents`, and project files/Git state in the selected workspace. Restart behavior and project ownership must be checked against the specific route; not every in-memory object is a durable database record.

## Project task board

The task board tracks durable project work items; it is intentionally separate from one-time scheduled Agent prompts. Work items are stored in a local SQLite database at `<projects_config_root>/.agents/taskboard.sqlite` (schema in [DATA_MODEL.md](DATA_MODEL.md#task-board-work-item)), while each item carries a `project_id` and may link to a conversation owned by that same project. The Starlette API exposes list/create/update/archive routes under `/api/taskboard/tasks`. Updates use a version field to reject stale writes, and archive is a soft delete. The React board is opened from the left navigation and occupies the main workspace; its current project is selected in the board header. It does not claim that a linked Agent conversation has completed a task: status changes remain explicit board actions.

## Project and application scope

- Projects are selected by local path and recorded in project history.
- Project files, sessions, rules, runs, and worktrees are associated with the project paths and `.agents` data described by the relevant routes.
- MCP/Skill installation and configuration are application-level, as accepted during the settings review; they are not isolated per project by the current product contract.
- The local path boundary is application policy. It is not an OS sandbox: terminal subprocesses run as the current Windows user and can access anything that user can access.

## Workflow and architecture instances

The UI exposes global templates and project-owned instances (lifecycle and record shapes: [DATA_MODEL.md](DATA_MODEL.md#template--instance--run-lifecycle); runnable example: [examples/workflow-quickstart](../examples/workflow-quickstart/README.md)). A template defines agent roles, responsibilities, prompt templates, model choices, and graph edges; the project instance is the copied, editable definition used for a real run. It does not capture a model credential. Each run creates isolated conversation sessions for its nodes and stores task input, node outputs, status snapshots, and bounded status events under the project `.agents/runs` directory.

The current runner is deliberately dependency-light: the UI schedules one node at a time and calls the existing chat SSE endpoint for model work; the backend owns isolated sessions, validates chat handoff data, validates legal run/node state transitions, and atomically persists each run update. Agent outputs are passed as structured records (`node_id`, title, edge relation/label, output). The runner waits for active branch inputs before a merge node, sends only outputs on active edges, routes condition and loop decisions through a strict `YES`/`NO` response, and caps loop iterations. One node's output is the handoff payload; there is no additional manager model call to rewrite every handoff. A final Supervisor turn reviews the collected results and returns the answer to the originating conversation.

This runtime is serial, so it favors predictable ordering and lower orchestration overhead over parallel branch execution. The scheduler still lives in the renderer, so closing/reloading the UI can interrupt scheduling even though the backend has persisted progress. Run events are currently stored with the run record; there is not yet a separate run-history query or resume endpoint. MCP/Skill references in a node are not executable node-level integrations unless the existing chat permissions attach them to that conversation. See [testing and limitations](TESTING.md) before treating editor node types as runtime executors.

## Trust boundaries

1. **Model provider:** user-configured remote service; prompts and selected project context may be sent to it.
2. **Local tools:** file, shell, Git, MCP and Skill actions can affect the local machine or project according to their implementation and permissions.
3. **External MCP/Skill packages:** repository metadata is not a security guarantee. Inspect code, command paths, environment variables, and network access before enabling.
4. **Loopback API:** binds to local machine in the desktop launcher. Keep it on loopback unless authentication and network exposure are deliberately designed.

This is an implementation overview, not a security certification or claim of operating-system isolation.

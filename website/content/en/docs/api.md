# Local API reference

The VeraAgent desktop UI talks to a local Starlette API. This page summarizes its route groups; the generated repository [API index](../../../../docs/API.md#route-index) has the complete parameters, errors, and implementation locations. This is an API for the local app, **not an authenticated public cloud API**.

## Conventions

| Item | Contract |
| --- | --- |
| Base URL | `http://127.0.0.1:<port>`; usually 8000, with 8001–8100 as desktop fallback |
| Authentication | None; keep on loopback. CORS is `*`. |
| Body | JSON with `snake_case` field names |
| Errors | Non-2xx responses generally contain `{"error":"<message>"}`; some errors are in Chinese |
| Common status codes | `400` invalid input; `403` rejected action/path; `404` missing; `409` conflict; `413` too large; `502`/`504` upstream marketplace errors |
| Project scope | Most project-data requests require a bound `project_id` |

`GET /api/health` checks liveness. `GET /api/topology` is the desktop launcher's readiness probe. Vite proxies `/api` during development.

## Chat stream (`chat.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/chat/stream` | Start one SSE turn; common fields: `thread_id`, `project_id`, `content`, `model_id`. Workflow runs also pass `workflow_stage`, `workflow_control`, and `workflow_input`. |
| POST | `/api/chat/confirm` | Answer an `approval_required` request |
| POST | `/api/chat/interrupt` | Interrupt a turn |
| POST | `/api/chat/pause`, `/api/chat/resume` | Pause/resume streaming within one turn; this does not resume a workflow run |

SSE events are `thinking` (status, **not hidden reasoning**), `text_chunk`, `tool_call`, `approval_required`, `tool_result` (display output capped at 5,000 characters), `subagent`, `context_management`, and final `finish`. The UI parser is in `frontend/src/api/chatApi.ts`.

## Project binding (`projects.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/projects` | Bound project history |
| GET | `/api/projects/current` | Current project |
| POST | `/api/projects/bind` | Bind an existing directory; `path` must exist |
| POST | `/api/projects/select-folder` | Open the system folder picker |
| PATCH / DELETE | `/api/projects/{project_id}` | Update/remove a project record |

Binding stores a path; it does not copy or isolate project files.

## Topology templates (`templates.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/templates/topology` | Built-in plus custom templates |
| POST | `/api/templates/topology` | Save a custom template. Organization templates must be one-root, acyclic agent trees. |

## Organization/workflow instances and runs (`groups.py`, `runs.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/groups` | List/create project instances |
| PATCH / DELETE | `/api/groups/{group_id}` | Update/delete an instance |
| POST | `/api/groups/instances` | Instantiate a template; 1–60 nodes and at most 120 edges |
| POST | `/api/groups/compose` | Write a protocol-level graph; many accepted node kinds lack executors |
| POST | `/api/groups/provision` | Provision node threads and related resources |
| GET | `/api/groups/{group_id}/registry` | Explicit agent registry |
| POST / DELETE | `/api/groups/{group_id}/edges` | Add/remove an edge |
| GET / POST | `/api/groups/{group_id}/threads` | Read/create node threads |
| POST | `/api/groups/{group_id}/runs` | Create a run with `project_id`, input (up to 100,000 characters), and string confirmation `"Y"`; creates isolated node threads |
| PATCH | `/api/groups/{group_id}/runs/{run_id}` | Validate and persist run/node state changes; the backend does not schedule nodes |

See the [run data model](../../../../docs/DATA_MODEL.md#run-record) for transitions and limits.

## Threads (`threads.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/threads` | List/create conversations |
| GET | `/api/threads/{id}/messages` | Read messages |
| PATCH / DELETE | `/api/threads/{id}` | Update/delete a conversation |
| POST | `/api/threads/{id}/messages/deliver` | Deliver the final workflow/organization review back to the initiating conversation |
| POST | `/api/threads/{id}/messages/truncate` | Truncate history from a user message to retry from that point |
| GET | `/api/threads/{id}/context-probe`, `/context-status` | Inspect context use against the selected model |
| GET | `/api/context-status` | Draft-state context status without `thread_id` |
| POST | `/api/threads/{id}/context-rebirth` | Compact/recreate an overlong workflow node thread |

## Task board (`taskboard.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/taskboard/tasks` | List project work items |
| POST | `/api/taskboard/tasks` | Create an item; title is 1–240 characters |
| PATCH | `/api/taskboard/tasks/{id}` | Update with current `version`; stale writes return 409 and the latest item |
| DELETE | `/api/taskboard/tasks/{id}` | Soft-archive an item |

Task-board items are persistent work items. Linking a chat does not automatically change their status. See the [task data model](../../../../docs/DATA_MODEL.md#task-board-work-item).

## One-off scheduled tasks (`tasks.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/tasks/scheduled` | List/create one-off scheduled agent prompts |
| PATCH | `/api/tasks/scheduled/{id}/toggle` | Enable/disable |
| POST | `/api/tasks/scheduled/{id}/run` | Trigger once now |
| DELETE | `/api/tasks/scheduled/{id}` | Delete |

These tasks live in `<project>/.agents/scheduled_tasks.json` and run through the app's background scheduler.

## Files and editing (`files.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/files/tree`, `/api/files/content` | Read file tree/text |
| GET | `/api/files/preview`, `/api/files/raw` | Preview or retrieve a file |
| PUT | `/api/files/content`, `/api/files/excel` | Save text or Excel content |
| POST | `/api/code/check-syntax`, `/api/code/search-symbols` | Syntax check or symbol search |

Paths are checked against the bound project as an **application-level policy, not an OS sandbox**.

## Git branches (`gitflow.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/topology`, `/api/gitflow/topology` | Launcher readiness and branch topology |
| GET / POST | `/api/branches` | List/create branches |
| DELETE | `/api/branches/{name}` | Delete a branch |
| POST | `/api/branches/checkout`, `/api/branches/merge` | Switch or merge branches |
| POST | `/api/merge-review` | Pre-merge review; model use depends on the request context |

## Git worktrees (`worktrees.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/worktrees/refs`, `/api/worktrees/diff` | Available refs and changes |
| POST | `/api/worktrees/stage`, `/api/worktrees/discard` | Stage or discard selected files |
| POST | `/api/worktrees/checkpoint`, `/api/worktrees/reset` | Commit or reset a worktree; reset may be `hard` |

These operate on node-specific local worktrees used by a workflow/organization run, not a general project-wide Git client.

## MCP servers and marketplace (`mcp.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/mcp/servers` | List/register servers |
| PUT | `/api/mcp/servers/{id}` | Update configuration |
| PATCH | `/api/mcp/servers/{id}/toggle` | Enable/disable |
| POST | `/api/mcp/servers/{id}/restart` | Restart connection |
| DELETE | `/api/mcp/servers/{id}` | Delete server |
| POST | `/api/mcp/scan` | Scan servers |
| GET | `/api/mcp/market` | Read marketplace |
| POST | `/api/mcp/market/install` | Install from marketplace |

Settings are application-level, not project-isolated. Marketplace listings are not security reviews.

## Skills and marketplace (`skills.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/skills` | List installed Skills |
| POST | `/api/skills/scan` | Scan local Skills |
| GET | `/api/skills/market` | Read marketplace |
| POST | `/api/skills/install` | Install a Skill |
| DELETE | `/api/skills/{name}` | Delete |
| PATCH | `/api/skills/{name}/toggle` | Enable/disable |

A Skill is instruction text injected into agent context and should be treated as untrusted. MCP is an external process/service connection.

## Settings (`settings.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/settings/models` | Read/save model configurations |
| PATCH / DELETE | `/api/settings/models/{id}` | Update/delete one model |
| POST | `/api/settings/models/test` | Test model connection |
| GET / POST | `/api/settings/permissions`, `/api/settings/rules`, `/api/settings/context` | Permissions, project rules, context settings |
| GET / POST | `/api/settings/user-memories` | Read/create user memories |
| PATCH / DELETE | `/api/settings/user-memories/{id}` | Update/delete one memory |

Model API keys are plaintext in `models_config.json` and omitted from API responses.

## Analytics (`analytics.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/analytics/dashboard` | Aggregate recent token use, cost, and activity from stored threads |

## Session routing and health (`sessions.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| POST | `/api/sessions/attach`, `/api/sessions/detach` | Attach/detach a thread to an organization/workflow session bus |
| POST | `/api/messages/send` | Route a message between attached sessions |

## Terminal (`terminal.py`)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/terminal/exec` | One-shot noninteractive command |
| WS | `/api/terminal/session?project_id=<id>` | PowerShell session in the project directory; `group_id` is also supported |

The process runs with the current Windows user's permissions. The WebSocket rejects a non-loopback `Origin`.

## API boundary

There is currently no caller authentication. Do not expose this port to a network as a multi-user service. For a new endpoint, update the route and frontend types, then the generated [API index](../../../../docs/API.md) and tests.

## Traces, memory, and improvement APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/traces`, `/api/traces/summary`, `/api/traces/{trace_id}` | List, aggregate, inspect |
| POST | `/api/traces/{trace_id}/feedback` | Independent user feedback |
| GET / POST | `/api/memories` | Query scoped records / create |
| PATCH / DELETE | `/api/memories/{memory_id}` | Update / soft-delete |
| GET / POST | `/api/memories/{memory_id}/history`, `/restore` | Versions / restore |
| GET / POST | `/api/memories/pending`, `/api/memories/pending/{change_id}` | List / accept or reject |
| GET | `/api/evolution/proposals` | List proposals |
| POST | `/api/evolution/analyze`, `/api/evolution/proposals/{proposal_id}/gate` | Model analysis / eval (costs apply) |
| POST | `/api/evolution/proposals/{proposal_id}/adopt`, `/reject`, `/rollback` | Adopt, reject, rollback |
| POST | `/api/evolution/monitor` | User-triggered online comparison |
| GET / PUT | `/api/settings/telemetry`, `/api/settings/memory` | Read / update settings |

See the generated [API index](../../../../docs/API.md) and [learning loop](../../../../docs/LEARNING_LOOP.md) for full paths and contracts. Adoption requires `{"confirm": true}`. The unauthenticated API remains loopback-only.

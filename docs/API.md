# HTTP API reference

The VeraAgent desktop UI talks to a local Starlette application created by
[`create_app`](../vera-agent/src/vera_agent/server/app.py). This document describes
the contract between `frontend/src/api/*.ts` and `vera-agent/src/vera_agent/server/routes/*.py`.

The route index at the end is **generated** from the source by
[`scripts/generate_api_index.py`](../scripts/generate_api_index.py) and checked in CI
(`python scripts/generate_api_index.py --check`). Keep the hand-written sections
above it accurate when you change a contract.

## Conventions

| Topic | Contract |
| --- | --- |
| Base URL | `http://127.0.0.1:<port>`; `start-desktop.ps1` uses 8000, or the first free port in 8001–8100. The UI reads `VITE_API_BASE_URL` at build time; in `npm run dev` Vite proxies `/api` to `VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`). |
| Authentication | None. The API trusts every caller and must stay on loopback. CORS is `*`; the terminal WebSocket additionally rejects non-loopback `Origin` headers. |
| Format | JSON request and response bodies. Field names are `snake_case` and the frontend types in `frontend/src/types/` keep them unchanged. |
| Errors | Non-2xx responses carry `{"error": "<message>"}`. `frontend/src/api/client.ts` throws `Error(error)`. Some messages are Chinese because they are shown in the UI as-is. |
| Status codes | `400` invalid input, `403` confirmation/permission refused or path outside the project, `404` unknown project/thread/item, `409` state conflict (stale `version`, invalid status transition, busy thread), `413` payload over a documented limit, `502`/`504` upstream market errors. |
| Project scoping | Most project data routes take `project_id` (query or body). It must match an entry in the project history; paths are resolved inside that project's folder. |
| Readiness | `GET /api/topology` returns 200 once the API is up; the desktop launcher polls it. `GET /api/health` is a lightweight liveness check. |

## Streaming endpoints

### `POST /api/chat/stream` (Server-Sent Events)

Runs one user turn. Main request fields: `thread_id` (created if absent), `project_id`,
`group_id`, `content`, `client_message_id`, `model_id`, `images`, `ephemeral`
(side chat, not persisted), and workflow fields used by the workflow runner:
`workflow_stage` (`supervisor_review` or `control_decision`), `workflow_control`
(`{type: "condition"|"loop", condition, ...}` for control decisions),
`workflow_input`, `workflow_upstream`, `workflow_context`.

The response is `text/event-stream`. Each event is `event: <name>` plus one JSON `data:` line:

| Event | Payload | Meaning |
| --- | --- | --- |
| `thinking` | `{step, content}` | Progress status text (not model reasoning). |
| `text_chunk` | `{content}` | Incremental assistant text. |
| `tool_call` | `{action_id, tool_name, args}` | The model requested a tool. |
| `approval_required` | `{action_id, tool_name, args, message}` | The permission policy requires the user to answer via `POST /api/chat/confirm` (`{thread_id, action_id, choice}`). |
| `tool_result` | `{action_id, tool_name, output, returncode}` | Tool finished; `output` is truncated to 5,000 characters. |
| `subagent` | subagent run record | Progress of a delegated Researcher/Reviewer run. |
| `context_management` | `{kind, timestamp, before_tokens, after_tokens, reason?}` | Conversation compaction happened. |
| `finish` | `{duration, steps, cost, total_cost, exit_status}` | Turn ended (always last). |

`POST /api/chat/interrupt`, `/pause`, and `/resume` control a running turn by `thread_id`.
The parser is `streamChat` in `frontend/src/api/chatApi.ts`.

### `WS /api/terminal/session`

Query: `project_id` or `group_id`. Opens a PowerShell process in the project directory.

| Direction | Message |
| --- | --- |
| server → client | `{"type": "connected", "shell", "cwd"}`, `{"type": "output", "data"}`, `{"type": "exit", "exit_code"}`, `{"type": "error", "message"}` |
| client → server | `{"type": "input", "data": "<text>"}` |

Commands run with the current Windows user's privileges.

## Key request bodies

These are the contracts most likely to be extended. Limits are enforced by the backend.

**`POST /api/templates/topology`** saves a custom template: `name` (required), `nodes`
(non-empty, unique non-empty `id`s), `edges` (each `source`/`target` must be a node id),
optional `template_id`, `description`, `topology_type`. Returns `201 {status, template}`.

**`POST /api/groups/instances`** creates a project-owned instance: `project_id`, `name`,
`group_mode` (`workflow` or `architecture`), `nodes` (1–60), `edges` (≤ 120), `goal`
(≤ 20,000 chars), `background` (≤ 50,000 chars), optional `template_id`,
`template_name`, `layout`. Returns `201 {group}`.

**`POST /api/groups/{group_id}/runs`** creates a run: `project_id`, `confirmation`
(must be the string `"Y"`, otherwise 403), `input` (non-empty, ≤ 100,000 chars),
optional `node_ids` subset. Returns `201 {run}` with one isolated session per node.

**`PATCH /api/groups/{group_id}/runs/{run_id}?project_id=`** updates `status`, `nodes`
(`[{node_id, status, output, error, inputs}]`), `final_output`, `error`. Status
transitions are validated; see [run state machine](DATA_MODEL.md#run-record).

**`POST /api/taskboard/tasks`**: `project_id`, `title` (1–240 chars), optional
`description` (≤ 20,000), `status`, `priority`, `labels` (≤ 20, each ≤ 48 chars).
**`PATCH /api/taskboard/tasks/{id}`** requires the current `version`; a stale version
returns `409 {error, item}` with the latest item. Allowed values are in
[DATA_MODEL.md](DATA_MODEL.md#task-board-work-item).

**`POST /api/projects/bind`**: `path` (existing folder), optional `name`, `project_id`,
`folders`, `repo_root`.

## Route index

"Frontend client" lists exported functions in `frontend/src/api/*.ts` that call the
path. A dash means no client wrapper: the route is used elsewhere (the terminal
WebSocket is opened in `frontend/src/stores/terminalStore.ts`, `/api/topology` is the
launcher readiness probe) or exists for agent/session wiring and tests.

<!-- routes:begin -->

_Generated by `scripts/generate_api_index.py` — 133 routes._

### `analytics.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/analytics/dashboard` | [`get_analytics_dashboard`](../vera-agent/src/vera_agent/server/routes/analytics.py#L62) | `project_id` | — | `fetchAnalyticsDashboard` |

### `chat.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/chat/stream` | [`chat_stream`](../vera-agent/src/vera_agent/server/routes/chat.py#L48) | — | — | `streamChat` |
| POST | `/api/chat/confirm` | [`chat_confirm`](../vera-agent/src/vera_agent/server/routes/chat.py#L81) | — | 400, 404 | `confirmApproval` |
| POST | `/api/chat/interrupt` | [`chat_interrupt`](../vera-agent/src/vera_agent/server/routes/chat.py#L103) | — | 400 | `interruptChat` |
| POST | `/api/chat/pause` | [`chat_pause`](../vera-agent/src/vera_agent/server/routes/chat.py#L137) | — | 400 | `pauseChat` |
| POST | `/api/chat/resume` | [`chat_resume`](../vera-agent/src/vera_agent/server/routes/chat.py#L153) | — | 400 | `resumeChat` |
| POST | `/api/chat/ephemeral/close` | [`close_ephemeral_chat`](../vera-agent/src/vera_agent/server/routes/chat.py#L169) | — | 400, 409 | `closeEphemeralChat` |

### `evolution.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/evolution/proposals` | [`list_proposals`](../vera-agent/src/vera_agent/server/routes/evolution.py#L62) | `status` | — | `fetchProposals` |
| GET | `/api/evolution/proposals/{proposal_id}` | [`get_proposal`](../vera-agent/src/vera_agent/server/routes/evolution.py#L68) | — | 404 | — |
| POST | `/api/evolution/analyze` | [`analyze`](../vera-agent/src/vera_agent/server/routes/evolution.py#L77) | — | 400 | `analyzeTraces` |
| POST | `/api/evolution/proposals/{proposal_id}/gate` | [`start_gate`](../vera-agent/src/vera_agent/server/routes/evolution.py#L85) | — | 400, 404, 409 | `startGate` |
| POST | `/api/evolution/proposals/{proposal_id}/adopt` | [`adopt_proposal`](../vera-agent/src/vera_agent/server/routes/evolution.py#L111) | — | 400, 404, 409 | `adoptProposal` |
| POST | `/api/evolution/proposals/{proposal_id}/reject` | [`reject_proposal`](../vera-agent/src/vera_agent/server/routes/evolution.py#L130) | — | 404, 409 | `rejectProposal` |
| POST | `/api/evolution/proposals/{proposal_id}/rollback` | [`rollback_proposal`](../vera-agent/src/vera_agent/server/routes/evolution.py#L143) | — | 404, 409 | `rollbackProposal` |
| POST | `/api/evolution/monitor` | [`run_monitor`](../vera-agent/src/vera_agent/server/routes/evolution.py#L160) | — | — | — |
| GET | `/api/evolution/drafts` | [`get_drafts`](../vera-agent/src/vera_agent/server/routes/evolution.py#L164) | — | — | — |
| POST | `/api/evolution/drafts/{trace_id}` | [`save_draft`](../vera-agent/src/vera_agent/server/routes/evolution.py#L168) | — | 400 | — |

### `files.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/files/tree` | [`get_files_tree`](../vera-agent/src/vera_agent/server/routes/files.py#L369) | `group_id`, `project_id` | 404 | `fetchFileTree` |
| GET | `/api/files/content` | [`get_file_content`](../vera-agent/src/vera_agent/server/routes/files.py#L400) | `group_id`, `path` | 400, 403, 404, 500 | `fetchFileContent`, `saveTextFile` |
| GET | `/api/files/preview` | [`get_file_preview`](../vera-agent/src/vera_agent/server/routes/files.py#L432) | `path` | 400, 403, 404 | `fetchFilePreview` |
| GET | `/api/files/raw` | [`get_raw_file`](../vera-agent/src/vera_agent/server/routes/files.py#L500) | `path` | 403, 404 | `getRawFileUrl` |
| PUT | `/api/files/content` | [`save_file_content`](../vera-agent/src/vera_agent/server/routes/files.py#L516) | — | 400, 403, 404, 415 | `fetchFileContent`, `saveTextFile` |
| PUT | `/api/files/excel` | [`save_excel_file`](../vera-agent/src/vera_agent/server/routes/files.py#L538) | — | 400, 403, 404 | `saveExcelFile` |
| POST | `/api/code/check-syntax` | [`check_syntax`](../vera-agent/src/vera_agent/server/routes/files.py#L562) | — | 400 | `checkCodeSyntax` |
| POST | `/api/code/search-symbols` | [`search_symbols`](../vera-agent/src/vera_agent/server/routes/files.py#L573) | — | 400 | `searchCodeSymbols` |

### `gitflow.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/topology` | [`get_topology`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L38) | — | — | — |
| GET | `/api/gitflow/topology` | [`get_gitflow_topology`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L45) | `project_id` | 400, 404 | `fetchGitFlowTopology` |
| GET | `/api/branches` | [`get_branches`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L137) | `project_id` | 404 | `createBranch`, `fetchBranches` |
| POST | `/api/branches` | [`create_branch`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L170) | — | 400, 404, 500 | `createBranch`, `fetchBranches` |
| DELETE | `/api/branches/{branch_name:path}` | [`delete_branch`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L195) | `project_id` | 400, 404, 409 | `deleteBranch` |
| POST | `/api/branches/checkout` | [`checkout_branch`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L214) | — | 400, 404, 500 | `checkoutBranch` |
| POST | `/api/branches/merge` | [`merge_branch`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L235) | — | 400, 404 | `mergeBranch` |
| POST | `/api/merge-review` | [`merge_review`](../vera-agent/src/vera_agent/server/routes/gitflow.py#L262) | — | 400, 404 | `requestMergeReview` |

### `groups.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/groups` | [`get_groups`](../vera-agent/src/vera_agent/server/routes/groups.py#L143) | `project_id` | 404 | `createGroup`, `fetchGroups` |
| POST | `/api/groups` | [`create_group`](../vera-agent/src/vera_agent/server/routes/groups.py#L227) | — | 400, 500 | `createGroup`, `fetchGroups` |
| PATCH | `/api/groups/{group_id}` | [`update_group`](../vera-agent/src/vera_agent/server/routes/groups.py#L254) | `project_id` | 400, 404, 500 | `deleteGroup`, `updateGroup` |
| DELETE | `/api/groups/{group_id}` | [`delete_group`](../vera-agent/src/vera_agent/server/routes/groups.py#L365) | `project_id` | 404, 500 | `deleteGroup`, `updateGroup` |
| GET | `/api/groups/{group_id}/threads` | [`get_group_threads`](../vera-agent/src/vera_agent/server/routes/groups.py#L400) | — | 404, 500 | `createGroupThread` |
| POST | `/api/groups/{group_id}/threads` | [`create_group_thread`](../vera-agent/src/vera_agent/server/routes/groups.py#L428) | `project_id` | 404, 500 | `createGroupThread` |
| POST | `/api/groups/instances` | [`create_group_instance`](../vera-agent/src/vera_agent/server/routes/groups.py#L533) | — | 400 | `createGroupInstance` |
| POST | `/api/groups/provision` | [`provision_group`](../vera-agent/src/vera_agent/server/routes/groups.py#L791) | — | 400, 404, 500 | `provisionGroup` |
| POST | `/api/groups/compose` | [`compose_group`](../vera-agent/src/vera_agent/server/routes/groups.py#L603) | — | 400, 404, 500 | `composeGroup` |
| GET | `/api/groups/{group_id}/registry` | [`get_group_registry`](../vera-agent/src/vera_agent/server/routes/groups.py#L906) | `project_id` | 404 | — |
| POST | `/api/groups/{group_id}/edges` | [`add_group_edge`](../vera-agent/src/vera_agent/server/routes/groups.py#L919) | — | 400 | — |
| DELETE | `/api/groups/{group_id}/edges` | [`remove_group_edge`](../vera-agent/src/vera_agent/server/routes/groups.py#L948) | — | 400 | — |

### `templates.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/templates/topology` | [`get_templates`](../vera-agent/src/vera_agent/server/routes/templates.py#L26) | — | — | `fetchTopologyTemplates`, `saveTopologyTemplate` |
| POST | `/api/templates/topology` | [`save_topology_template`](../vera-agent/src/vera_agent/server/routes/templates.py#L52) | — | 400 | `fetchTopologyTemplates`, `saveTopologyTemplate` |

### `runs.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/groups/{group_id}/runs` | [`create_group_run`](../vera-agent/src/vera_agent/server/routes/runs.py#L32) | — | 400, 403, 404, 413 | `createGroupRun` |
| PATCH | `/api/groups/{group_id}/runs/{run_id}` | [`update_group_run`](../vera-agent/src/vera_agent/server/routes/runs.py#L115) | `project_id` | 400, 404, 409, 413 | `updateGroupRun` |

### `mcp.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/mcp/servers` | [`get_mcp_servers`](../vera-agent/src/vera_agent/server/routes/mcp.py#L51) | — | — | `createMcpServer`, `fetchMcpServers` |
| POST | `/api/mcp/servers` | [`create_mcp_server`](../vera-agent/src/vera_agent/server/routes/mcp.py#L89) | — | 400, 409 | `createMcpServer`, `fetchMcpServers` |
| PUT | `/api/mcp/servers/{server_id}` | [`update_mcp_server`](../vera-agent/src/vera_agent/server/routes/mcp.py#L130) | — | 400, 404 | `deleteMcpServer`, `updateMcpServer` |
| POST | `/api/mcp/scan` | [`scan_mcp_servers`](../vera-agent/src/vera_agent/server/routes/mcp.py#L57) | — | — | `scanMcpServers` |
| PATCH | `/api/mcp/servers/{server_id}/toggle` | [`toggle_mcp_server`](../vera-agent/src/vera_agent/server/routes/mcp.py#L154) | — | 404 | `toggleMcpServer` |
| POST | `/api/mcp/servers/{server_id}/restart` | [`restart_mcp_server`](../vera-agent/src/vera_agent/server/routes/mcp.py#L173) | — | 404 | `restartMcpServer` |
| DELETE | `/api/mcp/servers/{server_id}` | [`delete_mcp_server`](../vera-agent/src/vera_agent/server/routes/mcp.py#L191) | — | 404 | `deleteMcpServer`, `updateMcpServer` |
| GET | `/api/mcp/market` | [`get_mcp_market`](../vera-agent/src/vera_agent/server/routes/mcp.py#L205) | `q`, `cursor` | 502, 504 | `fetchMcpMarket` |
| POST | `/api/mcp/market/install` | [`install_mcp_market`](../vera-agent/src/vera_agent/server/routes/mcp.py#L300) | — | 400, 404, 409, 502 | `installMcpFromMarket` |

### `memories.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/memories` | [`list_memories`](../vera-agent/src/vera_agent/server/routes/memories.py#L49) | — | 400 | `fetchMemories` |
| POST | `/api/memories` | [`create_memory`](../vera-agent/src/vera_agent/server/routes/memories.py#L70) | — | 400 | `fetchMemories` |
| GET | `/api/memories/pending` | [`list_pending`](../vera-agent/src/vera_agent/server/routes/memories.py#L127) | — | — | `fetchPendingChanges` |
| POST | `/api/memories/pending/{change_id}` | [`resolve_pending`](../vera-agent/src/vera_agent/server/routes/memories.py#L131) | — | 400, 404 | `resolvePendingChange` |
| PATCH | `/api/memories/{memory_id}` | [`update_memory`](../vera-agent/src/vera_agent/server/routes/memories.py#L87) | — | 400, 404 | `deleteMemory`, `updateMemory` |
| DELETE | `/api/memories/{memory_id}` | [`delete_memory`](../vera-agent/src/vera_agent/server/routes/memories.py#L102) | — | 404 | `deleteMemory`, `updateMemory` |
| GET | `/api/memories/{memory_id}/history` | [`memory_history`](../vera-agent/src/vera_agent/server/routes/memories.py#L108) | — | 404 | `fetchMemoryHistory` |
| POST | `/api/memories/{memory_id}/restore` | [`restore_memory`](../vera-agent/src/vera_agent/server/routes/memories.py#L115) | — | 400, 404 | `restoreMemoryVersion` |
| GET | `/api/settings/memory` | [`get_memory_settings`](../vera-agent/src/vera_agent/server/routes/memories.py#L144) | — | — | — |
| PUT | `/api/settings/memory` | [`update_memory_settings`](../vera-agent/src/vera_agent/server/routes/memories.py#L148) | — | 400 | — |

### `projects.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/projects` | [`get_projects`](../vera-agent/src/vera_agent/server/routes/projects.py#L33) | — | — | `fetchProjects` |
| GET | `/api/projects/current` | [`get_current_project`](../vera-agent/src/vera_agent/server/routes/projects.py#L39) | — | — | `fetchCurrentProject` |
| POST | `/api/projects/bind` | [`bind_project`](../vera-agent/src/vera_agent/server/routes/projects.py#L126) | — | 400 | `bindProjectFolder` |
| POST | `/api/projects/select-folder` | [`select_project_folder`](../vera-agent/src/vera_agent/server/routes/projects.py#L115) | — | 500 | `selectProjectFolder` |
| DELETE | `/api/projects/{project_id}` | [`delete_project`](../vera-agent/src/vera_agent/server/routes/projects.py#L222) | — | 404 | `deleteProjectHistory`, `updateProject` |
| PATCH | `/api/projects/{project_id}` | [`update_project`](../vera-agent/src/vera_agent/server/routes/projects.py#L175) | — | 400, 404 | `deleteProjectHistory`, `updateProject` |

### `sessions.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/health` | [`health`](../vera-agent/src/vera_agent/server/routes/sessions.py#L24) | — | — | — |
| POST | `/api/sessions/attach` | [`attach_session`](../vera-agent/src/vera_agent/server/routes/sessions.py#L29) | — | 400, 500 | — |
| POST | `/api/sessions/detach` | [`detach_session`](../vera-agent/src/vera_agent/server/routes/sessions.py#L48) | — | 400, 500 | — |
| POST | `/api/messages/send` | [`send_message`](../vera-agent/src/vera_agent/server/routes/sessions.py#L66) | — | 400 | — |

### `settings.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/settings/models` | [`get_models`](../vera-agent/src/vera_agent/server/routes/settings.py#L129) | — | — | `createModel`, `fetchModels` |
| POST | `/api/settings/models` | [`save_models`](../vera-agent/src/vera_agent/server/routes/settings.py#L135) | — | 400 | `createModel`, `fetchModels` |
| PATCH | `/api/settings/models/{model_id}` | [`update_single_model`](../vera-agent/src/vera_agent/server/routes/settings.py#L167) | — | 400, 404 | `deleteModel`, `patchModel` |
| DELETE | `/api/settings/models/{model_id}` | [`delete_single_model`](../vera-agent/src/vera_agent/server/routes/settings.py#L211) | — | 404 | `deleteModel`, `patchModel` |
| POST | `/api/settings/models/test` | [`test_model_connection`](../vera-agent/src/vera_agent/server/routes/settings.py#L227) | — | 400 | `testModelConnection` |
| GET | `/api/settings/permissions` | [`get_permissions`](../vera-agent/src/vera_agent/server/routes/settings.py#L267) | — | — | `fetchPermissions`, `savePermissions` |
| POST | `/api/settings/permissions` | [`save_permissions`](../vera-agent/src/vera_agent/server/routes/settings.py#L273) | — | 400 | `fetchPermissions`, `savePermissions` |
| GET | `/api/settings/rules` | [`get_rules`](../vera-agent/src/vera_agent/server/routes/settings.py#L287) | — | — | `saveRules` |
| POST | `/api/settings/rules` | [`save_rules`](../vera-agent/src/vera_agent/server/routes/settings.py#L292) | — | 400, 413 | `saveRules` |
| GET | `/api/settings/context` | [`get_context_settings`](../vera-agent/src/vera_agent/server/routes/settings.py#L306) | — | — | `fetchRules`, `saveContextSettings` |
| POST | `/api/settings/context` | [`save_context_settings_route`](../vera-agent/src/vera_agent/server/routes/settings.py#L310) | — | 400 | `fetchRules`, `saveContextSettings` |
| GET | `/api/settings/user-memories` | [`get_user_memories`](../vera-agent/src/vera_agent/server/routes/settings.py#L325) | — | — | `fetchUserMemories`, `saveUserMemory` |
| POST | `/api/settings/user-memories` | [`create_user_memory`](../vera-agent/src/vera_agent/server/routes/settings.py#L329) | — | 400 | `fetchUserMemories`, `saveUserMemory` |
| PATCH | `/api/settings/user-memories/{memory_id}` | [`update_user_memory`](../vera-agent/src/vera_agent/server/routes/settings.py#L347) | — | 400, 404 | `deleteUserMemory`, `saveUserMemory` |
| DELETE | `/api/settings/user-memories/{memory_id}` | [`remove_user_memory`](../vera-agent/src/vera_agent/server/routes/settings.py#L374) | — | 404 | `deleteUserMemory`, `saveUserMemory` |

### `skills.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/skills` | [`list_skills`](../vera-agent/src/vera_agent/server/routes/skills.py#L60) | — | — | `fetchSkills` |
| POST | `/api/skills/scan` | [`scan_skills`](../vera-agent/src/vera_agent/server/routes/skills.py#L68) | — | — | `scanSkills` |
| GET | `/api/skills/market` | [`get_skills_market`](../vera-agent/src/vera_agent/server/routes/skills.py#L115) | `q` | 502 | `fetchSkillsMarket` |
| POST | `/api/skills/install` | [`install_skill`](../vera-agent/src/vera_agent/server/routes/skills.py#L280) | — | 400, 409, 502 | `installSkill` |
| DELETE | `/api/skills/{skill_name}` | [`delete_skill`](../vera-agent/src/vera_agent/server/routes/skills.py#L76) | — | 404, 500 | `deleteSkill` |
| PATCH | `/api/skills/{skill_name}/toggle` | [`toggle_skill`](../vera-agent/src/vera_agent/server/routes/skills.py#L94) | — | 404 | `toggleSkill` |

### `taskboard.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/taskboard/tasks` | [`list_work_items`](../vera-agent/src/vera_agent/server/routes/taskboard.py#L151) | `project_id` | 400, 404 | `createWorkItem`, `fetchWorkItems` |
| POST | `/api/taskboard/tasks` | [`create_work_item`](../vera-agent/src/vera_agent/server/routes/taskboard.py#L167) | — | 400, 404 | `createWorkItem`, `fetchWorkItems` |
| PATCH | `/api/taskboard/tasks/{item_id}` | [`update_work_item`](../vera-agent/src/vera_agent/server/routes/taskboard.py#L224) | — | 400, 404, 409 | `archiveWorkItem`, `updateWorkItem` |
| DELETE | `/api/taskboard/tasks/{item_id}` | [`archive_work_item`](../vera-agent/src/vera_agent/server/routes/taskboard.py#L306) | — | 404 | `archiveWorkItem`, `updateWorkItem` |

### `tasks.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/tasks/scheduled` | [`get_scheduled_tasks`](../vera-agent/src/vera_agent/server/routes/tasks.py#L291) | — | — | `createScheduledTask`, `fetchScheduledTasks` |
| POST | `/api/tasks/scheduled` | [`create_scheduled_task`](../vera-agent/src/vera_agent/server/routes/tasks.py#L296) | — | 400 | `createScheduledTask`, `fetchScheduledTasks` |
| PATCH | `/api/tasks/scheduled/{task_id}/toggle` | [`toggle_scheduled_task`](../vera-agent/src/vera_agent/server/routes/tasks.py#L336) | — | 404 | `toggleScheduledTask` |
| POST | `/api/tasks/scheduled/{task_id}/run` | [`run_scheduled_task`](../vera-agent/src/vera_agent/server/routes/tasks.py#L347) | — | 404, 409 | `runScheduledTask` |
| DELETE | `/api/tasks/scheduled/{task_id}` | [`delete_scheduled_task`](../vera-agent/src/vera_agent/server/routes/tasks.py#L363) | — | 404 | `deleteScheduledTask` |

### `terminal.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/terminal/exec` | [`exec_terminal_command`](../vera-agent/src/vera_agent/server/routes/terminal.py#L44) | — | 400, 404, 408, 500 | `execTerminalCommand` |
| WS | `/api/terminal/session` | [`terminal_session`](../vera-agent/src/vera_agent/server/routes/terminal.py#L112) | `group_id`, `project_id` | — | — |

### `threads.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/threads` | [`get_all_threads`](../vera-agent/src/vera_agent/server/routes/threads.py#L32) | — | — | `createThread`, `fetchThreads` |
| POST | `/api/threads` | [`create_thread`](../vera-agent/src/vera_agent/server/routes/threads.py#L86) | — | 404 | `createThread`, `fetchThreads` |
| GET | `/api/threads/{thread_id}/messages` | [`get_thread_messages`](../vera-agent/src/vera_agent/server/routes/threads.py#L131) | — | — | `fetchThreadMessages` |
| POST | `/api/threads/{thread_id}/messages/deliver` | [`deliver_orchestration_result`](../vera-agent/src/vera_agent/server/routes/threads.py#L149) | — | 400, 404, 409 | `deliverOrchestrationResult` |
| POST | `/api/threads/{thread_id}/messages/truncate` | [`truncate_from_user_message`](../vera-agent/src/vera_agent/server/routes/threads.py#L216) | — | 400, 404, 409 | `truncateThreadFromMessage` |
| PATCH | `/api/threads/{thread_id}` | [`update_thread`](../vera-agent/src/vera_agent/server/routes/threads.py#L249) | — | 400 | `deleteThread`, `updateThread` |
| DELETE | `/api/threads/{thread_id}` | [`delete_thread`](../vera-agent/src/vera_agent/server/routes/threads.py#L279) | — | — | `deleteThread`, `updateThread` |
| GET | `/api/threads/{thread_id}/context-probe` | [`probe_thread_context`](../vera-agent/src/vera_agent/server/routes/threads.py#L297) | — | — | `probeThreadContext` |
| GET | `/api/threads/{thread_id}/context-status` | [`get_thread_context_status`](../vera-agent/src/vera_agent/server/routes/threads.py#L327) | `model_id` | 400, 404, 500 | `fetchThreadContextStatus` |
| GET | `/api/context-status` | [`get_thread_context_status`](../vera-agent/src/vera_agent/server/routes/threads.py#L327) | `model_id` | 400, 404, 500 | `fetchDraftContextStatus` |
| POST | `/api/threads/{thread_id}/context-rebirth` | [`rebirth_group_thread_context`](../vera-agent/src/vera_agent/server/routes/threads.py#L442) | — | 400, 403, 404, 409 | `rebirthGroupThreadContext` |

### `traces.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/traces` | [`list_traces`](../vera-agent/src/vera_agent/server/routes/traces.py#L40) | — | 400 | `fetchTraces` |
| GET | `/api/traces/summary` | [`trace_summary`](../vera-agent/src/vera_agent/server/routes/traces.py#L57) | — | — | `fetchTraceSummary` |
| GET | `/api/traces/{trace_id}` | [`get_trace`](../vera-agent/src/vera_agent/server/routes/traces.py#L62) | — | 404 | `fetchTrace` |
| POST | `/api/traces/{trace_id}/feedback` | [`add_trace_feedback`](../vera-agent/src/vera_agent/server/routes/traces.py#L69) | — | 400, 404 | `sendTraceFeedback` |
| GET | `/api/settings/telemetry` | [`get_telemetry_settings`](../vera-agent/src/vera_agent/server/routes/traces.py#L93) | — | — | — |
| PUT | `/api/settings/telemetry` | [`update_telemetry_settings`](../vera-agent/src/vera_agent/server/routes/traces.py#L97) | — | 400 | — |

### `worktrees.py`

| Method | Path | Handler | Query | Error statuses | Frontend client |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/worktrees/refs` | [`get_worktree_refs`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L45) | `project_id`, `branch` | 404 | `fetchWorktreeRefs` |
| GET | `/api/worktrees/diff` | [`get_worktree_diff`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L68) | `group_id`, `worktree_path`, `project_id`, `base_ref` | 400, 404 | `fetchWorktreeDiff` |
| POST | `/api/worktrees/stage` | [`stage_worktree_file`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L184) | — | 400, 404, 500 | `stageWorktreeFile` |
| POST | `/api/worktrees/discard` | [`discard_worktree_file`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L205) | — | 400, 404 | `discardWorktreeFile` |
| POST | `/api/worktrees/checkpoint` | [`create_checkpoint`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L228) | — | 400, 404, 500 | `createWorktreeCheckpoint` |
| POST | `/api/worktrees/reset` | [`reset_worktree`](../vera-agent/src/vera_agent/server/routes/worktrees.py#L256) | — | 400, 404, 500 | — |

<!-- routes:end -->

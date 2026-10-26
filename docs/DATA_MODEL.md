# Data model and local storage

VeraAgent keeps all state on the local machine as JSON files plus one SQLite
database. Nothing is synced. This page lists what is written, where, and the
shape of the core records. API contracts are in [API.md](API.md).

## Storage roots

`ServerState` ([`server/state.py`](../vera-agent/src/vera_agent/server/state.py)) uses two roots:

| Root | Value | Holds |
| --- | --- | --- |
| `projects_config_root` (application root) | `repo_root` passed to `create_app`; defaults to the API process working directory. `start-desktop.ps1` starts Uvicorn in `vera-agent/`, so the desktop app uses `<checkout>/vera-agent/.agents/`. | Application-scoped settings, templates, task board, Skills |
| `root_path` (bound project) | Folder of the currently bound project | Project sessions, workflow instances and runs, scheduled tasks |

Both locations are named `.agents/` and are ignored by Git. Back them up before
moving, deleting, or re-cloning a checkout. The pywebview window stores browser
data separately in `%LOCALAPPDATA%\VeraAgent\WebView2`, and the Python CLI `.env`
lives in `VERA_GLOBAL_CONFIG_DIR` (see [CONFIGURATION.md](CONFIGURATION.md)).

## File layout

```text
<projects_config_root>/.agents/
├── projects_history.json        # bound projects (id, name, path, folders, is_git, active_branch, ...)
├── models_config.json           # model profiles, INCLUDING API KEYS in plain text
├── permissions_config.json      # permission policy (see below)
├── mcp_servers.json             # MCP server registry
├── skills_config.json           # {"disabled_skills": [...]}
├── skills/<name>/SKILL.md       # installed Skills
├── registries/                  # market caches (e.g. skills-market-cache.json)
├── templates/topology/<template_id>.json   # custom topology templates
├── taskboard.sqlite             # task board work items (WAL mode)
├── user_context.json            # user rules and context settings
├── user_memories.json           # legacy profile memories; imported once into memory.db, then unused
├── memory.db                    # scoped memories, versions, pending changes, embeddings (SQLite + FTS5)
├── memory_config.json           # memory backend, consolidation, recall budgets
├── traces.db                    # turn traces, spans and scores (SQLite)
├── telemetry_config.json        # local tracing and optional Langfuse export (may hold a Langfuse key)
├── evolution_config.json        # Critic/eval models, low-score threshold, gate repeats
├── evals/
│   ├── cases/<id>.yaml          # project eval cases (built-in cases ship in vera_agent/evals/cases/)
│   ├── drafts/<trace_id>.yaml   # case drafts from low-score traces (accept: TODO)
│   ├── profiles/<id>.json       # immutable agent profiles
│   └── reports/<report_id>.json # vera-eval reports
└── evolution/
    ├── proposals/<id>/proposal.json, diff.md
    └── rolled_back/<id>/        # Skills moved out on rollback

<project>/.agents/
├── sessions/<thread_id>.json    # one ThreadSession per conversation
├── groups/<group_id>.json       # workflow / architecture instances and groups
├── runs/<group_id>/<run_id>.json   # workflow runs
├── registries/<group_id>.json   # explicit agent registry of a group
├── scheduled_tasks.json         # one-time scheduled Agent prompts
└── mcp/                         # optional project-local MCP server discovered by /api/mcp/scan
```

**Secrets:** `models_config.json` stores provider API keys unencrypted; API
responses strip `api_key`. MCP server `env`/`headers` may also contain secrets.
Never commit or share `.agents/`.

## Topology template

Built-in templates are `TopologyTemplate` objects in
[`session/templates.py`](../vera-agent/src/vera_agent/session/templates.py)
(`supervisor_dev` is an organization; `sequential_workflow`, `adversarial_audit`, and
`swarm_mesh` are workflows).

Organizations (`topology_type: "architecture"`) must be reporting trees: one top role,
one direct superior per role, no cycles, agent nodes only. The API rejects other shapes
when creating or updating an instance and when saving an organization template, and the
editor only builds reporting lines through "add subordinate / add peer". Workflows need a
single start node; cycles are expressed with a loop node.
`GET /api/templates/topology` serializes them and adds `id = role_key`,
`type = "agent"` to nodes and `source`/`target` to edges, then merges custom
templates. A custom template with the same `template_id` overrides a built-in one.

| Field | Type | Notes |
| --- | --- | --- |
| `template_id` | string | Generated as `tpl_<10 hex>` when omitted |
| `name`, `description` | string | |
| `topology_type` | string | `workflow`, `architecture`, `supervisor`, `custom`, ... |
| `nodes` | `WorkflowNodeDefinition[]` | Unique non-empty `id` |
| `edges` | `WorkflowEdgeDefinition[]` | `source`/`target` must be node ids |
| `is_custom` | bool | `true` for user-saved templates |

## Workflow node and edge

Mirrors `WorkflowNodeDefinition` / `WorkflowEdgeDefinition` in
[`frontend/src/types/project.ts`](../frontend/src/types/project.ts).

| Node field | Meaning |
| --- | --- |
| `id`, `title`, `type` | `type` is one of the editor node types (`agent`, `start`, `condition`, `loop`, `output`, ...) |
| `role`, `role_key` | Role label used for the node's session |
| `prompt_template` | System prompt for the node; may use `{{goal}}` |
| `responsibilities`, `constraints`, `output_spec`, `background` | Prompt context for the node |
| `allowed_tools` | Tool names the node may use |
| `position`, `config`, `thread_id` | Editor layout, type-specific config, linked thread |

| Edge field | Meaning |
| --- | --- |
| `source`, `target` | Node ids |
| `relation`, `label` | Passed to the target with the upstream output (e.g. `YES`/`NO` branch labels) |

**Runtime support:** the current runner executes `agent` nodes through the chat
stream and treats `condition` and `loop` nodes as control decisions (their
session gets only the internal `__orchestration_control__` tool and must answer
`YES` or `NO`). Other editor node types are stored but are not separate executors.

## Instance (group) record

Created by `POST /api/groups/instances`
([`create_group_instance`](../vera-agent/src/vera_agent/server/routes/groups.py)) and
stored at `<project>/.agents/groups/<group_id>.json`.

| Field | Notes |
| --- | --- |
| `group_id` | `flow_<10 hex>` |
| `project_id`, `project_path` | Owning project |
| `group_mode` | `workflow` (graph of steps) or `architecture` (organization of roles) |
| `name`, `goal` (≤ 20,000), `background` (≤ 50,000) | Project-specific context copied into every node session |
| `template_id`, `template_name`, `topology_type` | Template provenance |
| `nodes` (1–60), `edges` (≤ 120), `layout` | Copied, editable definition |
| `thread_ids` | Sessions materialized for the nodes |
| `is_pinned`, `is_archived`, `created_at` | UI state |

Instances never store model credentials.

## Run record

Created by `POST /api/groups/{group_id}/runs` and stored at
`<project>/.agents/runs/<group_id>/<run_id>.json`.

| Field | Notes |
| --- | --- |
| `run_id` | `run_<12 hex>` |
| `group_id`, `project_id`, `input` (≤ 100,000) | |
| `status` | Run status (below) |
| `sessions` | `[{node_id, thread_id, title, prompt_template}]`, one isolated session per node |
| `nodes` | `[{node_id, status, output (≤ 200,000), error (≤ 4,000), inputs}]` |
| `nodes[].inputs` | Provenance `[{node_id, title, output, relation?, label?}]`, ≤ 50 items, ≤ 250,000 chars total |
| `final_output`, `error` | Set at the end |
| `events` | `run_created`, `run_status {from, to}`, `node_status {node_id, status}`; capped at 5,000 |

Run status transitions (`update_group_run` in [`routes/runs.py`](../vera-agent/src/vera_agent/server/routes/runs.py)):

| From | Allowed to |
| --- | --- |
| `ready` | `running`, `failed`, `cancelled` |
| `running` | `completed`, `failed`, `cancelled` |
| `completed`, `failed`, `cancelled` | terminal |

A run can only become `completed` when every node is `completed` or `skipped`.

Node status transitions:

| From | Allowed to |
| --- | --- |
| `pending` | `pending`, `running`, `completed`, `failed`, `skipped` |
| `running` | `running`, `completed`, `failed` |
| `completed` | `running` (loop re-entry), `completed` |
| `failed`, `skipped` | unchanged |

## Template → instance → run lifecycle

1. **Template**: a reusable set of roles and connections (built-in or saved custom JSON).
2. **Instance**: `POST /api/groups/instances` copies the template into a project,
   adds the project `goal`/`background`, and materializes one session per node.
3. **Run**: the user confirms with `Y`; `POST /api/groups/{group_id}/runs` creates
   isolated sessions for this run. The UI scheduler in
   [`workflowRunner.ts`](../frontend/src/components/tools/workflowRunner.ts) (driven by `WorkflowTab.tsx`) starts at the
   root `agent` node, calls `POST /api/chat/stream` once per node with the upstream
   outputs on active edges, resolves `condition`/`loop` nodes with a `control_decision`
   call, and PATCHes the run after each node.
4. **Supervisor and delivery**: a final `supervisor_review` turn reviews collected
   outputs; `POST /api/threads/{thread_id}/messages/deliver` writes the answer into the
   conversation that started the run.

Execution is serial. Because scheduling lives in the renderer, reloading the UI
stops a run in progress; persisted node states remain, but there is no resume endpoint.

## Task board work item

Table `work_items` in `<projects_config_root>/.agents/taskboard.sqlite`
([`taskboard.py`](../vera-agent/src/vera_agent/server/routes/taskboard.py)).

| Column | Notes |
| --- | --- |
| `id` | 32-char hex |
| `identifier` | `VA-<12 upper hex>`, unique, shown in the UI |
| `project_id` | Must exist in project history |
| `title` (1–240), `description` (≤ 20,000) | |
| `status` | `backlog`, `todo` (default), `in_progress`, `blocked`, `in_review`, `done`, `canceled` |
| `priority` | `urgent`, `high`, `medium` (default), `low`, `none` |
| `labels` | JSON array, ≤ 20 unique labels of ≤ 48 chars |
| `sort_order` | Integer order within a status column |
| `thread_id` | Optional linked conversation; must belong to the same project |
| `version` | Incremented on every update; PATCH must send the current value (optimistic concurrency) |
| `archived_at` | Set by DELETE (soft archive); archived items are hidden from lists |
| `created_at`, `updated_at` | UTC ISO-8601 |

Linking a conversation does not change status automatically; status changes are explicit.

## ThreadSession

Dataclass in [`session/thread.py`](../vera-agent/src/vera_agent/session/thread.py),
persisted as `sessions/<thread_id>.json`.

| Field | Notes |
| --- | --- |
| `thread_id` | `th_<12 hex>` |
| `role` | `main`, `researcher`, `reviewer`, or a workflow role |
| `title`, `is_pinned`, `is_archived` | UI state |
| `parent_thread_id`, `group_id`, `project_id` | Ownership |
| `messages` | Model-facing transcript (OpenAI-style message dicts) |
| `cost`, `n_calls` | Accumulated usage |
| `metadata` | Free-form; workflow sessions store `workflow_run_id`, `workflow_node_id`, `system_prompt`, `allowed_tools`, `group_goal`, ... |
| `created_at`, `updated_at` | Unix timestamps |

## Model profile

`models_config.json` holds `{"models": [...]}`; validated by `_validate_model` in
[`settings.py`](../vera-agent/src/vera_agent/server/routes/settings.py). Resolution of the
active model is in [`model_profile.py`](../vera-agent/src/vera_agent/server/model_profile.py).

| Field | Constraint |
| --- | --- |
| `id`, `name` | Required, unique `id` |
| `provider` | `openai`, `anthropic`, `google`, `deepseek`, `openrouter`, `ollama`, `qwen`, `zhipu`, `moonshot`, `siliconflow`, `volcengine`, `xai`, `mistral`, `custom` |
| `base_url` | Required absolute http(s) URL |
| `api_key` | Secret; never returned by the API |
| `is_default`, `enabled`, `supports_images` | Booleans; at most one default |
| `thinking_mode` | `auto`, `enabled`, `disabled` |
| `context_window` ≤ 2,000,000; `output_tokens`/`max_tokens` ≤ 393,216; `max_tool_calls` ≤ 500 | Integers; output ≤ context window |
| `temperature` 0–2, `top_p` 0–1, `top_k` 1–100 | Optional sampling parameters |

## Permission policy

`permissions_config.json`, normalized by
[`server/permissions.py`](../vera-agent/src/vera_agent/server/permissions.py):

| Field | Values |
| --- | --- |
| `default_mode` | `manual` (default), `auto`, `allow_all` |
| `approval_actions` | Subset of `read`, `create`, `edit`, `terminal`, `search`, `mcp`, `delegation` that require approval |
| `operation_scope` | `project_write_external_readonly` (default) or `project_only` |
| `max_tool_attempts` | 1–20, default 3 |

Legacy modes are migrated: `human`/`confirm` → `manual`, `yolo` → `auto`.
Tool names map to categories in `permission_category` (e.g. `bash` → `terminal`,
`web_search` → `search`, `mcp__*` → `mcp`).

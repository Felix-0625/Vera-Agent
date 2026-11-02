# Learning API contracts

This supplements the [generated route index](API.md#route-index). All examples use the local
API origin, JSON bodies and snake_case fields. Errors have an `error` string. Do not expose the
unauthenticated API outside loopback. Analyze and gate operations call configured models and cost money.

## Versioned memory

### List and create

`GET /api/memories` returns `200 {"memories": [MemoryRecord, ...]}`.

| Query | Default | Meaning |
| --- | --- | --- |
| `scope` | all scopes | `user`, `project` or `session`; unsupported values return 400 |
| `scope_id` | all ids in the selected scope | Project id or thread id; use with `scope` |
| `kind` | all kinds | `profile`, `preference`, `habit`, `feedback`, `fact`, `episode`, `rule`; unsupported values currently fall back to all kinds |
| `status` | `active` | `active`, `deleted`, `superseded` or `any`; unsupported values return 400 |

For example: `/api/memories?scope=project&scope_id=proj_example&kind=preference`.
This panel API can list selected scopes; turn-time recall separately enforces the current
user/project/session visibility set.

`POST /api/memories` creates a user-authored record:

```json
{
  "scope": "project",
  "scope_id": "proj_example",
  "kind": "preference",
  "content": "Run python -m unittest -q after edits."
}
```

`kind` and nonempty `content` are required. `scope` defaults to `user`; use the project or
thread id as `scope_id` for meaningful project/session isolation (the write API currently
also accepts an empty id). Ordinary content is normalized to one line and limited to 500 characters.
User-authored rule content allows up to 1500 characters and preserves internal whitespace;
the Critic's rule proposals have their own smaller 300-character limit. Credentials are rejected.
Returns `201 {"memory": MemoryRecord}`; invalid scope/kind/content returns 400.

A `MemoryRecord` contains `memory_id`, `scope`, `scope_id`, `kind`, `content`, `source`,
`confidence`, `status`, `version`, creation/update/use timestamps and provenance metadata.
The authoritative fields are in [records.py](../vera-agent/src/vera_agent/memory/records.py);
the frontend mirror is [learning.ts](../frontend/src/types/learning.ts).

### Revise, delete and restore

| Request | Body | Success | Errors |
| --- | --- | --- | --- |
| `PATCH /api/memories/{memory_id}` | Required `content`; optional `kind` | `200 {memory}` | 400 invalid write, 404 missing record |
| `DELETE /api/memories/{memory_id}` | none | `200 {"status":"deleted"}` (soft delete) | 404 missing record |
| `GET /api/memories/{memory_id}/history` | none | `200 {"history":[...]}` | 404 missing history |
| `POST /api/memories/{memory_id}/restore` | `{"version":1}` | `200 {memory}` with a new current version | 400 invalid version, 404 missing record/version |

Restoring does not remove history. The write service protects rule authorship: model
consolidation cannot create or overwrite a rule.

### Pending changes

`GET /api/memories/pending` returns `200 {"changes":[...]}`. Changes include `change_id`,
`operation`, `memory_id`, scope/kind/content, reason, provenance, timestamps and `status`.

Resolve one with `POST /api/memories/pending/{change_id}`:

```json
{"accept": true}
```

`accept` must be a JSON boolean; use `false` to reject. Success is `200 {"change":...}`.
400 indicates an invalid decision or write; 404 indicates an unknown change. An accepted
update/delete creates history. Rejected changes preserve the current record.

## Traces and feedback

`GET /api/traces` returns `200 {"traces":[TraceSummary,...]}`.

| Query | Default | Meaning |
| --- | --- | --- |
| `project_id`, `thread_id` | all | Filter exact ids |
| `days` | all time | Positive numeric lookback; absent, invalid or nonpositive values mean all time |
| `below_score` | none | Numeric outcome threshold; nonnumeric input returns 400 |
| `limit` | 50 | Integer, clamped by storage to 1–500; noninteger input returns 400 |

`GET /api/traces/summary?days=30` returns `200 {"task_types":[...]}` with counts and success
rates grouped by task type. `GET /api/traces/{trace_id}` returns `200 {"trace":...}`, including
spans and separate scores, or 404. The data definitions are [trace.py](../vera-agent/src/vera_agent/telemetry/trace.py)
and the frontend's [learning types](../frontend/src/types/learning.ts).

`POST /api/traces/{trace_id}/feedback` accepts:

```json
{"value": 1, "comment": "The result met the acceptance criteria."}
```

`value` must convert to a number in [0,1]; optional `comment` is truncated to 500 characters.
Returns `201 {"score":...}`; invalid values return 400 and an unknown trace returns 404.
This stores `user_feedback`. It does not rewrite the trace's verification result or prove a test passed.

## Improvement proposals

| Request | Body/query | Success | Errors |
| --- | --- | --- | --- |
| `GET /api/evolution/proposals` | optional `status` query | `200 {proposals:[...]}` | — |
| `GET /api/evolution/proposals/{id}` | none | `200 {proposal}` | 404 |
| `POST /api/evolution/analyze` | none; models/settings come from config | `200 {traces,drafts,proposals}` | 400 invalid model/config |
| `POST /api/evolution/proposals/{id}/gate` | none | `202 {status:"started",proposal_id}` | 400 case-only proposal, 404 missing, 409 already running |
| `POST /api/evolution/proposals/{id}/adopt` | `confirm:true`; optional `override:false` | `200 {proposal}` | 400 missing confirmation, 404 missing, 409 adoption refused |
| `POST /api/evolution/proposals/{id}/reject` | none | `200 {proposal}` | 404 missing, 409 adopted/rolled-back proposal |
| `POST /api/evolution/proposals/{id}/rollback` | optional `reason` (truncated to 300 chars) | `200 {proposal}` | 404 missing, 409 invalid state |

For example, normal adoption uses:

```json
{"confirm": true, "override": false}
```

**202 means the gate started, not that it passed.** Poll the proposal endpoint or list; inspect
`gate_running`, its gate report and recommendation. A completed recommendation may be
`no_difference` or a regression. An explicit `override` expresses the user's decision to
override a gate recommendation; it does not waive content validation, provenance or confirmation.
Nothing is adopted by the offline example or by simply viewing proposals.

Proposal records and gate metrics are defined in [proposals.py](../vera-agent/src/vera_agent/evolution/proposals.py)
and [compare.py](../vera-agent/src/vera_agent/evals/compare.py). State transitions, training/holdout/guard
separation and rollback criteria are explained in [LEARNING_LOOP.md](LEARNING_LOOP.md).

`POST /api/evolution/monitor` returns `{reports:[...]}` and may roll back degraded adoptions;
it is a mutation, not a passive statistics query. `GET /api/evolution/drafts` returns `{drafts:[...]}`.
`POST /api/evolution/drafts/{trace_id}` requires a `case` object, validates the case and returns
`201 {path}`; invalid cases return 400. These operations are not scheduled automatically.

## Configuration

`GET /api/settings/memory` returns the current normalized configuration; `PUT` accepts a
partial object with keys/defaults listed in [LEARNING_LOOP.md](LEARNING_LOOP.md#configuration-files).
The response is the normalized configuration. A malformed/non-object request returns 400.
Consolidation remains off until explicitly configured.

`GET`/`PUT /api/settings/telemetry` use `enabled` and a nested `langfuse` object. Partial writes
are supported; an omitted/empty secret does not erase a saved Langfuse secret. Responses omit
`secret_key` and provide `secret_key_set`. Invalid JSON or an unsupported exporter host returns 400.
Local tracing is on by default; Langfuse export is off by default.

Configuration files and environment variables are catalogued in [CONFIGURATION.md](CONFIGURATION.md).
Treat memory, trace exports and optional backend configuration as private application data.

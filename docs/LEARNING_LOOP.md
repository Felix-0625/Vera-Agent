# Evaluation, memory, and self-improvement

By default, VeraAgent records each non-ephemeral desktop chat turn as a trace, scores it, keeps scoped long-term memory,
and can propose improvements to its own rules and Skills. A proposal only takes effect after it
passes an evaluation gate and you approve it. The new telemetry, memory, eval, and proposal records are stored locally under
`<projects_config_root>/.agents/`; Langfuse and Mem0 are optional adapters that are off by default.

```text
chat turn ──► trace + spans ──► outcome scores ──┬──► memory: episodes, consolidated facts (fast loop)
 (run_turn)    (telemetry/)      (scoring.py)    │
                                                 └──► low-score traces ──► Critic proposal
                                                       ──► eval gate (train → holdout → guard)
                                                       ──► your approval ──► rule memory / Skill
                                                       ──► online monitor ──► keep or roll back (slow loop)
```

## 1. One turn, one execution path

`server/chat/turn.py:run_turn(ctx)` runs a user turn and yields its SSE events. The HTTP route
only builds the `TurnContext` (`server/chat/turn_setup.py:prepare_turn`), connects MCP servers,
and forwards events. The eval runner calls the same function without a UI.

Two things are injected through the context:

| Piece | Desktop | Eval runner |
| --- | --- | --- |
| `TurnControl` (`server/chat/control.py`) | Backed by `ServerState`, so `/api/chat/interrupt`, `/pause`, `/resume` work | `TurnControl.standalone` |
| `ApprovalPolicy` | `InteractiveApprovalPolicy`: waits for `/api/chat/confirm` (300 s timeout = reject) | `AutoApprovalPolicy`: approves file edits in the sandbox and only the case's allow-listed commands |

`AutoApprovalPolicy` never approves a terminal command that contains `;`, `&`, `|`, `<`, `>`,
backticks, `$(` or a newline, so a pattern such as `python -m pytest*` cannot approve
`python -m pytest; curl …`. Web search, MCP and subagents are rejected in eval runs.

## 2. Traces and scores

`telemetry/` follows Langfuse's trace / observation / score model.

- A **trace** is one turn: input, final answer, exit status, steps, cost, task type, recalled memory ids.
- **Spans** are model calls (tokens, cost), tool calls (arguments, return code, approval result:
  approved / rejected / corrected with the `O:` text) and subagent runs. Tool output is truncated
  to 2,000 characters and every stored string goes through the secret filter (`utils/redact.py`).
- Traces live in `.agents/traces.db` (SQLite). Ephemeral side chats are never traced.

Scores are kept under separate names so weak and strong evidence never mix:

| Score | Source | Rule |
| --- | --- | --- |
| `turn_signal` | `signal` | 1.0, lowered by a model error (0), interruption (≤0.2), tool limit (≤0.3), each rejected approval (−0.2) and each `O:` correction (−0.3) |
| `verification` | `verifier` | The last test/build command of the turn (pytest, npm test/build, cargo, go, make, ruff, tsc …): 1 if it exited 0, else 0 |
| `outcome` | — | `verification` when the turn ran one, otherwise `turn_signal` |
| `user_followup` | `heuristic` | Your next message in the thread scores the previous turn: correction / revert wording → 0, acceptance / "继续" → 1. Shown on its own; never changes `outcome` |
| `user_feedback` | `user` | 👍 / 👎 in the 执行记录 panel |
| `eval_accept` | `eval` | Acceptance script result of an eval run |

Return codes of ordinary commands (a `grep` that finds nothing), commands that only mention a verifier, shell compositions, and pure version/help queries do not overwrite verification scores.
`outcome ≥ 0.5` counts as a success in the success-rate views.

Optional Langfuse export: `PUT /api/settings/telemetry` with
`{"langfuse": {"enabled": true, "host": "https://…", "public_key": "…", "secret_key": "…"}}`.
Enabling it **sends each (redacted) trace to that server**. The secret key is never returned by the API.

## 3. Evals of the real product

`evals/` measures the desktop pipeline itself (prompt assembly, memory recall, Skills,
permission gate, tools). The inherited `run/benchmarks/swebench.py` drives the mini agent path and
skips those layers, so it is not used here.

- **Cases** (`evals/cases/*.yaml`, plus `<config root>/.agents/evals/cases/`): task, fixture files,
  acceptance script (exit 0 = pass), allowed commands, tool budget. Splits:
  `train` (the Critic may see these), `holdout` (decides whether a proposal helps; only aggregate
  numbers are stored on proposals) and `guard` (core abilities that must never regress).
  40 built-in cases ship: 16 train, 14 holdout, 10 guard.
- **Profiles** (`evals/profile.py`): an immutable, versioned overlay of rules, prompt text, Skills
  and seed memories. `baseline` is the product as shipped. Saved under `.agents/evals/profiles/`.
- **Sandbox** (`evals/sandbox.py`): each run gets a new git repository with the fixture and its own
  config root, so it never reads or writes your real `.agents/`. Only `models_config.json` is copied.
  Commands still run as your Windows user; the allow-list is what limits them.
- **Comparison** (`evals/compare.py`): each case runs N times per profile; per-case pass-rate
  differences give a win rate, a 95 % percentile-bootstrap interval of the mean difference (fixed
  seed), and an exact sign test. Verdict: `better` if the interval is above 0, `worse` if below,
  otherwise `no_difference`. A single case can never be `better`.

If an existing virtual environment has not refreshed its console entry points, use
`.\.venv\Scripts\python.exe -m vera_agent.evals.cli` in place of `vera-eval.exe`.

```powershell
cd vera-agent
.\.venv\Scripts\vera-eval.exe list
.\.venv\Scripts\vera-eval.exe run --profile baseline --split guard
.\.venv\Scripts\vera-eval.exe run --profile baseline --profile cand-xyz --split holdout --repeats 3
```

`vera-eval` calls your configured model and **costs money**: cases × profiles × repeats turns.
Run it from the folder whose `.agents/` holds your model settings (`--config-root`). Reports are
saved to `.agents/evals/reports/`. `tests/check-all.ps1` only tests the runner with scripted
models; real-model evals are never part of the gate.

## 4. Long-term memory

`memory/` replaces the flat `user_memories.json` list (imported once on first start; the old
file is left untouched and old memory ids keep working).

- **Scopes:** `user` (all conversations), `project` (one project id), `session` (one thread).
  A turn sees its user, project and session scopes only.
- **Kinds:** `profile`, `preference`, `habit`, `feedback`, `fact`, `episode`, `rule`. Rules can
  only be written by you or by adopting a proposal; the model can never write one.
- **Versions:** every change adds a version with reason, actor and trace id; delete is a soft
  delete; any version can be restored (as a new version).
- **Storage:** `.agents/memory.db`, SQLite with an FTS5 `trigram` index, which matches Chinese
  text without a word segmenter (queries are split into 3-character windows). Optional embeddings
  via `litellm.embedding` and reranking via `litellm.rerank`.
- **Recall** (`memory/retrieve.py`): keyword (+ vector) relevance × confidence × recency (90-day
  half-life), filtered by a minimum relevance, then filled into a token budget (default 150).
  Rules you wrote get their own budget (default 120), so preferences can never push one out. The
  result is inserted as `<runtime_memory>` in the system prompt. Rules from adopted proposals are
  not part of recall; see step 3 of the next section.
- **Episodes:** after each finished turn with tool calls, one `episode` memory records goal,
  tools used, pitfalls (failed / rejected tools), result and outcome score in the project scope.
- **Consolidation** (`memory/consolidate.py`, off by default): Mem0's extract → retrieve similar →
  decide ADD / UPDATE / DELETE / NONE pipeline, run in the background after a turn with the model
  you choose. ADD is stored at once with confidence 0.6. UPDATE and DELETE become **pending
  changes** you accept or reject in the 长期记忆 panel, or apply automatically after
  `auto_apply_hours` if you set it (still undoable). Only your message and the final answer are
  given to the model, never tool output, so text planted in files cannot become a memory.
- **Mem0 backend** (optional): `"backend": "mem0"` in `memory_config.json` with `mem0ai` installed
  yourself. Its default configuration calls external LLM and embedding APIs; supply a local
  `mem0_config` if data must stay on this machine. Version history and pending changes stay local.

## 5. Proposals, gate, adoption, rollback

`evolution/` is the slow loop. Nothing in it runs on a timer; you start each step.

1. **Analyze** (改进提案 → 分析, `POST /api/evolution/analyze`): the Critic model reads up to 8
   recent desktop traces with `outcome` strictly below 0.5 (eval traces excluded) and returns up
   to 3 proposals: `rule`, `skill`, `prompt_overlay` or `eval_case`. Tool inputs and outputs are wrapped in
   `<untrusted_tool_output>` and described as data. Proposals that are too long, contain secrets,
   have an invalid Skill name, or try to disable approvals / skip tests / ignore instructions are
   dropped. Holdout and guard eval traces are refused outright. Each low-score trace also gets an
   eval case draft in `.agents/evals/drafts/` with `accept: TODO`; it becomes a `train` case only
   after you write a real acceptance check.
2. **Gate** (运行评测): the baseline is the product plus every proposal already adopted in that
   scope, so each new proposal is judged on top of the earlier ones. Baseline vs. baseline +
   proposal on train (must not be `worse`), holdout (must be `better`), guard (zero regressions),
   stopping at the first failure. Default 3 repeats. Only a proposal that clears all three is
   `recommended`.
3. **Adopt** (采纳, requires `{"confirm": true}`): a rule (≤300 chars) or prompt overlay (≤1,500
   chars, line breaks kept) is stored as a `rule` memory, and every later turn renders the adopted
   set through `evolution/active_profile.py` with the same function the gate used, outside the
   memory budget. What the gate measured is therefore what you get. Adopting a rule identical to
   one that already exists in the same scope is refused, so a later rollback can never delete your own rule.
   A Skill is written to `.agents/skills/<name>/SKILL.md` with
   `origin: evolved`, the proposal id, source traces and the holdout delta in its frontmatter, and
   is used under the normal permission policy. Existing Skills are never overwritten.
4. **Monitor** (`POST /api/evolution/monitor`): compares the mean `outcome` of scoped desktop traces in
   the 14 days before and after adoption. Once at least 10 scored traces exist after adoption, a
   drop of 0.15 or more rolls the proposal back automatically (rule soft-deleted, Skill moved to
   `.agents/evolution/rolled_back/`). This is an observational check, so rollback is reversible.

The optimizer never writes `evals/cases/`, the acceptance scripts, or the scorers.

## Configuration files

| File (`<config root>/.agents/`) | Keys | Default |
| --- | --- | --- |
| `telemetry_config.json` | `enabled`, `langfuse.{enabled,host,public_key,secret_key}` | tracing on, Langfuse off |
| `memory_config.json` | `backend` (`sqlite`/`mem0`), `consolidation` (`off`/`task_end`), `consolidation_model_id`, `auto_apply_hours`, `embedding_model`, `rerank_model`, `token_budget`, `rule_token_budget`, `mem0_config` | `sqlite`, `off`, —, `null`, —, —, 150, 120 |
| `evolution_config.json` | `critic_model_id`, `eval_model_id`, `low_score_threshold`, `gate_repeats` | default model, default model, 0.5, 3 |

## Known limits

- Task types are keyword-based (fix, test, review, refactor, feature, question, chat); they are a
  grouping aid, not a classifier.
- `user_followup` is a phrase heuristic and is often `None`; that is intentional.
- With 14 holdout cases a real but small improvement often ends as `no_difference`. Add project
  cases from drafts to make the gate more sensitive.
- The online monitor cannot separate an adoption's effect from other changes in the same weeks.

See the [learning-loop diagram](../website/diagrams/learning-loop-en.svg) and [editable diagrams](../website/diagrams/system-design.drawio).

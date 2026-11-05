# Evaluation and self-improvement (RSI)

How VeraAgent measures itself and how a measured result turns into a change of behaviour.
Tracing, memory and configuration files are in [LEARNING_LOOP.md](LEARNING_LOOP.md); request and
response shapes are in [LEARNING_API.md](LEARNING_API.md).

## The idea in one paragraph

Evaluation answers "did this configuration do better on tasks it has never been tuned on?".
Self-improvement answers "what should change?". Neither is enough alone: a Critic that proposes
changes without a gate adds noise, and a gate without proposals changes nothing. VeraAgent joins
them in one loop where every step that changes behaviour needs a measurement **and** the user.

```text
low-score traces ─► Critic ─► proposal ─► eval gate ─► user adopts ─► active profile
   (telemetry)      (reads)    (draft)   (train→holdout→guard)         (every turn)
        ▲                                                                   │
        └────────────── online monitor: outcome before vs after ◄───────────┘
                         (rolls back if the mean drops ≥ 0.15)
```

## Components and their single job

| Module | Job | Never does |
| --- | --- | --- |
| `telemetry/scoring.py` | Turn a finished turn into an `outcome` score | Judge eval runs (they use acceptance scripts) |
| `evals/cases.py` | Load cases and their `train` / `holdout` / `guard` split | Get written by the optimizer |
| `evals/runner.py` | Run one case through the real chat pipeline in a sandbox | Raise on agent failure; it records `error` for crashes |
| `evals/compare.py` | Paired comparison of two profiles: win rate, bootstrap interval, verdict | Count crashed runs as failures |
| `evolution/critic.py` | Propose at most 3 changes from low-score traces | See `holdout` / `guard` traces or follow tool output |
| `evolution/gate.py` | Decide `recommended` / `not_recommended` | Adopt anything |
| `evolution/adoption.py` | Apply or roll back an approved proposal | Run without `{"confirm": true}` |
| `evolution/active_profile.py` | Render adopted rules exactly as the gate rendered the candidate | Use the memory recall budget |
| `evolution/monitor.py` | Compare real-use outcomes before and after adoption | Run on a timer |

## Evaluation

A **case** is a task, fixture files, an acceptance script (exit 0 = pass), the commands the agent
may run, and a tool budget. Splits have different jobs:

| Split | Who may see it | Purpose |
| --- | --- | --- |
| `train` | The Critic and the user | Quick sanity check; the candidate must not be worse |
| `holdout` | Only aggregate counts are stored | Decides whether a proposal helps |
| `guard` | Only aggregate counts are stored | Core abilities; zero regressions allowed |

Forty cases ship (16 train, 14 holdout, 10 guard). Project cases go in
`<config root>/.agents/evals/cases/`.

Each run uses a fresh git repository and its own config root, so it never touches your real
`.agents/`. A run that crashes (model error, timeout, network) is recorded with `error` and is
**left out** of every pass rate; a provider outage must not look like a regression.

### Comparing two profiles

Both profiles run every case `N` times (default 3), interleaved per case so model drift does not
favour one side. `evals/compare.py` then works on per-case pass-rate differences:

- `mean_delta` with a 95 % percentile-bootstrap interval over cases (fixed seed, reproducible).
- `win_rate` and an exact sign test, reported for reading, not used for the verdict.
- Verdict: `better` if the interval is above 0, `worse` if below, otherwise `no_difference`.
  One case can never be `better`.

With 14 holdout cases a small real improvement usually ends as `no_difference`. That is the
intended result: a gate that says "yes" on weak evidence would be worse than no gate.

## The gate

`gate_proposal` builds the baseline as the product **plus every proposal already adopted in that
scope**, so each proposal is judged on top of the earlier ones. The candidate is the baseline plus
the proposal. Stages run in order and stop at the first failure (`evolution/gate.py:run_gate`):

| Stage | Passes when |
| --- | --- |
| `train` | No crashed runs and verdict is not `worse` |
| `holdout` | No crashed runs and verdict is `better` |
| `guard` | No crashed runs and no case the baseline always passed was failed even once by the candidate |

Only a proposal that clears all stages is `recommended`. Any crashed run rejects the stage with a
"run the gate again" reason instead of deciding on partial data.

## From proposal to behaviour

1. **Analyze** (`POST /api/evolution/analyze`): the Critic reads up to 8 recent low-score desktop
   traces. Tool output is wrapped as untrusted data. Proposals that are too long, contain secrets,
   or try to switch off approvals or tests are dropped. Each trace also gets an eval-case draft with
   `accept: TODO`; it becomes a `train` case only after you write a real acceptance check.
2. **Gate** (`POST .../gate`): runs in the background and **costs money** (cases x 2 profiles x
   repeats model turns).
3. **Adopt** (`POST .../adopt` with `{"confirm": true}`): a rule (≤300 characters) or prompt overlay
   (≤1,500) becomes a `rule` memory; a Skill is written to `.agents/skills/<name>/SKILL.md`.
   `active_profile.py` renders adopted rules with the same function the gate used, so what was
   measured is what runs. Only `recommended` proposals can be adopted unless the user passes
   `override`.
4. **Monitor** (`POST /api/evolution/monitor`, user-triggered): compares the mean `outcome` of
   desktop traces in the 14 days before and after adoption, scoped to the proposal's project for
   project rules. It needs at least 10 scored traces in **both** windows, then rolls back on a drop
   of 0.15 or more. Rollback soft-deletes the rule memory or moves the Skill to
   `.agents/evolution/rolled_back/`, so it can be inspected and re-adopted.

## Safety properties

- The optimizer never writes cases, acceptance scripts or scorers.
- Holdout and guard results are stored as aggregates only; the Critic refuses their traces.
- Nothing runs on a timer. Analyze, gate and monitor are explicit user actions.
- Rules from adoption bypass the recall budget so a preference can never push one out.

## Known limits

- The two scripted-model tests in `tests/evolution/` prove the logic, not that a real model
  improves. A real check is `vera-eval run` with a configured model.
- `outcome` for real use is a proxy: the last test or build command, or approval signals. Turns
  without a verifier are scored by `turn_signal` alone.
- The monitor is observational. Other changes in the same two weeks also move the mean.

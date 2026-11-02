# Memory and evaluation quickstart

Verify two product boundaries: project-scoped, versioned memory and an evaluation that uses
the same `run_turn` pipeline as chat. This example uses synthetic data and a **scripted provider**.
The file edit, test command, acceptance script, approvals and trace scoring are real; the provider
responses are fixed fixtures. A pass does not measure a real model or prove that an RSI proposal improves it.

## Prerequisites and run

Install the backend using the [development setup](../../docs/DEVELOPMENT.md). Git must be on PATH
because every evaluation creates a fresh repository. From the repository root:

```powershell
.\vera-agent\.venv\Scripts\python.exe examples\learning-loop\verify.py
```

No app server or API key is needed. There are no paid provider requests. An assertion or failed
acceptance exits nonzero; success prints JSON containing:

```json
{
  "provider": "scripted",
  "paid_model_calls": 0,
  "memory": {
    "chinese_recall": true,
    "project_isolation": true,
    "accept_reject": true,
    "version_restore": true
  },
  "evaluation": {
    "case_id": "example-fix-add",
    "passed": true,
    "steps": 3,
    "verification": 1
  }
}
```

## What runs

1. Create temporary SQLite memory storage. Retrieve a Chinese preference in project A and
   verify that project B cannot retrieve it.
2. Propose an update; check it stays pending, accept it, reject a deletion and restore version 1.
3. Load [`cases/fix-add.yaml`](cases/fix-add.yaml) into a fresh eval sandbox. Its initial `add`
   subtracts instead of adding. The scripted provider requests an edit and a real unittest command.
4. Require the independent acceptance script to pass and the trace's verification score to be 1.

Memory and eval sandboxes are temporary and removed on exit. Repeated runs create fresh state.
Your app configuration and the committed fixture are untouched. No profile or RSI proposal is adopted.

## Optional: run this case with a real model

Configure a model in the desktop app first. From the repository root, explicitly run:

```powershell
.\vera-agent\.venv\Scripts\vera-eval.exe run --config-root vera-agent --profile baseline --cases-dir examples\learning-loop\cases --case example-fix-add
```

**This command calls the configured provider and costs money.** The explicit case id limits the
run to this example. Its output is not guaranteed: inspect the acceptance result and errors.
Reports are written to `vera-agent/.agents/evals/reports/`; individual runs use isolated repositories.
Do not share reports without inspecting their conversation and tool content.

To assess an improvement, derive a profile and compare repeated, paired cases using the train,
holdout and guard procedure in [LEARNING_LOOP.md](../../docs/LEARNING_LOOP.md). A single passing
example is insufficient evidence of improvement. Read [the learning API](../../docs/LEARNING_API.md)
for memory and proposal request/response contracts.

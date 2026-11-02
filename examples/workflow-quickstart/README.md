# Workflow quickstart

A complete, reproducible walkthrough of VeraAgent's core idea: **define a
workflow or organization template, instantiate it in a project, and invoke it
from a conversation**, with the task tracked on the project task board.

```text
templates/*.json  ──save──▶  template library  ──instantiate──▶  project instance
                                                                       │
task board item ◀── track ── conversation ── "调用工作流 …" ──▶  run (one session per node)
                                                                       │
                                      Supervisor review ──▶ answer delivered to the conversation
```

## Contents

| Path | Purpose |
| --- | --- |
| `templates/review-pipeline.workflow.json` | Workflow: 需求分析 → 方案评审 → YES/NO 判断 → 整理结论 / 列出补充项 |
| `templates/small-team.architecture.json` | Organization: one lead managing an implementer and a tester |
| `demo-project/` | A tiny project to bind: `requirements.md` (input) and `AGENTS.md` (read-only rules) |
| `setup_demo.py` | Creates the project binding, templates, instance, and task board item through the HTTP API |

Template files use the same JSON shape as `POST /api/templates/topology`; see
[docs/DATA_MODEL.md](../../docs/DATA_MODEL.md#topology-template). Node prompts may use
`{{input}}` (run input), `{{upstream}}` (outputs on active incoming edges), and
`{{goal}}` (instance goal). Condition edges select a branch with
`config.sourceHandle` = `"true"` (YES) or `"false"` (NO).

## 1. Check it without a model (30 seconds)

From the repository root, after the [development setup](../../docs/DEVELOPMENT.md)
(the in-process check needs the test client):

```powershell
.\vera-agent\.venv\Scripts\python.exe examples\workflow-quickstart\setup_demo.py --dry-run
```

This starts the API in-process with a temporary data directory and a copy of
`demo-project/`, then calls the real routes. It prints the created project, template,
instance, task, and run IDs. No model is called, nothing is written to your
VeraAgent data, and the run record is created but not executed. The same check runs
in CI (`tests/test_examples.py`).

## 2. Try it in the desktop app

1. Start VeraAgent (`.\start-desktop.ps1`) and configure a model under **设置 → 模型**.
2. In another terminal, load the example into the running app:

   ```powershell
   .\vera-agent\.venv\Scripts\python.exe examples\workflow-quickstart\setup_demo.py
   ```

   Use `--base-url http://127.0.0.1:<port>` if the launcher chose a port other than 8000.
   This copies the synthetic project to `scratch/examples/workflow-quickstart`, binds that
   copy, saves the two `example_` templates, creates the workflow instance and adds a task
   board item. The committed fixture is never bound or modified. Set `--workspace <path>`
   to choose another demo copy. Repeat setup reuses the same instance and labeled task,
   and preserves their edits; it refreshes the two example templates.

   Prefer clicking? Do the same in the UI: bind the folder from the project selector,
   open **工作流模板**, recreate a template from the JSON, and create an instance in the project.
3. Open the task board: the item **评审登录限流需求** is in *Todo*.
4. Start a conversation in the demo project and send:

   > 调用工作流 示例：需求评审工作流，请评审 requirements.md 中的登录限流需求：列出验收标准与风险，判断是否可以进入开发。

   Confirm with **Y**. The workflow panel shows each node's state; the condition node
   answers YES/NO and only that branch runs. A final Supervisor review returns the
   answer to the conversation.
5. Link the conversation to the task board item and move it to *Done* when you accept the result.
6. Inspect the evidence: `<workspace>/.agents/runs/<group_id>/<run_id>.json` holds every
   node's status, inputs (with provenance), and output.

To try the organization template, create an *architecture* instance from
**示例：小型研发组织** in the same project and invoke it the same way.

## Expected result and cleanup

The dry run exits 0 and prints `project_id`, the two `template_ids`, a `group_id`,
`task_identifier`, `run_id` and all five `run_nodes`. IDs vary. `executed` is `false` and
`model_calls` is `0`: creating a run is not executing it. `--create-run` against a live API
also only creates a new ready record, and intentionally creates one each time.

In a live run, require completed nodes on one selected branch, a skipped unused branch and
a final result in the originating conversation. Model text and the branch choice vary.
Do not mark the task done merely because setup succeeded.

The live workspace is an ignored copy and can be reused. To retire it, remove its task and
project binding in the app first, close related conversations, then remove only that workspace
folder. The two global templates named **示例：…** remain until you remove them in the template
library. The script never deletes app configuration or user work as a reset operation.

## Limits

- Runs execute serially and are scheduled by the UI; reloading the window stops a run.
- Node `allowed_tools` restrict tools, but file and terminal tools are still subject to
  the global permission settings and are not an OS sandbox.
- Results depend on the configured model; this example does not ship expected outputs.

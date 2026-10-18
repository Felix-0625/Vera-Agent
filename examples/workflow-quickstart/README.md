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

From the repository root, after installing the backend (`docs/INSTALL_WINDOWS.md`):

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
   This binds `examples/workflow-quickstart/demo-project` (VeraAgent writes its
   `.agents/` folder there; it is Git-ignored), saves both templates, creates the
   workflow instance, and adds a task board item.

   Prefer clicking? Do the same in the UI: bind the folder from the project selector,
   open **工作流模板**, recreate a template from the JSON, and create an instance in the project.
3. Open the task board: the item **评审登录限流需求** is in *Todo*.
4. Start a conversation in the demo project and send:

   > 调用工作流 示例：需求评审工作流，请评审 requirements.md 中的登录限流需求：列出验收标准与风险，判断是否可以进入开发。

   Confirm with **Y**. The workflow panel shows each node's state; the condition node
   answers YES/NO and only that branch runs. A final Supervisor review returns the
   answer to the conversation.
5. Link the conversation to the task board item and move it to *Done* when you accept the result.
6. Inspect the evidence: `demo-project/.agents/runs/<group_id>/<run_id>.json` holds every
   node's status, inputs (with provenance), and output.

To try the organization template, create an *architecture* instance from
**示例：小型研发组织** in the same project and invoke it the same way.

## Limits

- Runs execute serially and are scheduled by the UI; reloading the window stops a run.
- Node `allowed_tools` restrict tools, but file and terminal tools are still subject to
  the global permission settings and are not an OS sandbox.
- Results depend on the configured model; this example does not ship expected outputs.

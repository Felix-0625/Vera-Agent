# VeraAgent examples

Small, runnable examples. Each one states what it proves and what it does not.
None of them ship API keys or claim model output.

| Example | What it shows | Needs a model? |
| --- | --- | --- |
| [`workflow-quickstart/`](workflow-quickstart/README.md) | **Start here.** Template → project instance → invocation from chat, tracked on the task board. Includes a workflow template with a YES/NO branch, an organization template, a demo project, and a setup script with a `--dry-run` check. | Only for the final run in the desktop app |
| [`sample-project/`](sample-project/README.md) | Minimal project with rules (`AGENTS.md`) and a task brief for a plain project conversation. | Yes, for the conversation |
| [`mcp-server/`](mcp-server/README.md) | Minimal read-only MCP server using the official Python SDK, with a stdio smoke test. | No |

Automated checks: `tests/test_examples.py` runs the workflow quickstart dry run and
validates the template files; `examples/mcp-server/test_client.py` performs a real
MCP stdio handshake. Both run in CI and in `tests/check-all.ps1`.

The website's [interactive demo](../website/playground/) is separate: it replays
scripted data in the browser and does not contact VeraAgent or a model provider.

## Concepts used by the examples

- **Template**: reusable roles (nodes) and connections (edges). Built-in templates live in
  `vera-agent/src/vera_agent/session/templates.py`; custom ones are saved as JSON.
- **Instance**: a template copied into one project, plus that project's goal and background.
  Two modes: `workflow` (steps with branches/loops) and `architecture` (an organization of roles).
- **Run**: one execution of an instance, started from a conversation after explicit `Y`
  confirmation. Each node gets an isolated session; outputs flow along active edges.

Details: [architecture](../docs/ARCHITECTURE.md), [data model](../docs/DATA_MODEL.md), [API](../docs/API.md).

Review code and permissions before connecting any third-party MCP server or Skill. A
small example is easier to inspect, but it does not make arbitrary extensions safe.

# vera-agent (Python backend)

The Python package behind the VeraAgent desktop app: the Agent loop, model adapters,
tools, session state, the local Starlette API, and the pywebview desktop shell.

## Setup

From this directory (see [../docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)):

```powershell
uv sync --locked --extra desktop --extra dev
```

Run the API alone:

```powershell
uv run uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000
```

The desktop window (`python -m vera_agent.desktop`) needs a built frontend; use
`../start-desktop.ps1` from the repository root to build and start everything.

## Layout

```text
src/vera_agent/
├── server/        Starlette API: app factory, ServerState, routes/ (one module per domain)
├── session/       ThreadSession, compaction, topology templates, group graph, router, registry
├── tools/         Agent tools: file primitives, subagents, web, handoff, Skills, code intelligence
├── telemetry/     Local traces, spans, separate outcome signals and optional export
├── memory/        Scoped/versioned SQLite memories, recall and optional consolidation
├── evals/         vera-eval cases, isolated runner, profiles and paired comparison
├── evolution/     Critic proposals, evaluation gates, adoption and rollback
├── agents/        DefaultAgent loop (inherited from mini-swe-agent)
├── models/        LiteLLM / OpenRouter / Portkey / Requesty adapters and tool-call parsing
├── environments/  Command execution backends (desktop uses local.py)
├── config/        YAML agent configs (subagents/, benchmarks/)
├── run/           Inherited CLI and benchmark runners (`vera`, `mini-extra`)
└── desktop.py     pywebview window
```

The full module map is in [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md); the HTTP
contract in [../docs/API.md](../docs/API.md); persisted data in [../docs/DATA_MODEL.md](../docs/DATA_MODEL.md).

## Checks

```powershell
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest tests
```

Tests use temporary directories and fake model responses; they do not prove live-provider
behavior. See [../docs/TESTING.md](../docs/TESTING.md).

Runnable [examples](../examples/README.md) include a workflow/API dry run, a memory/eval
check with a scripted provider and real tools, and a read-only MCP stdio server. Install dev
dependencies for their offline checks. Paid provider steps are separate and explicitly marked.

The group API entry is `server/routes/groups.py`; its handlers use separate lifecycle,
member, instance, materialization/composition and registry modules. Chat prompt rendering
and subagent execution adapters are also separate from their public orchestration entry points.

## Inherited CLI

The `vera` / `vera-agent` / `mini` and `mini-extra` console scripts are the single-agent
CLI and benchmark tools inherited from mini-swe-agent. They are kept working and tested,
but the desktop app does not use them. Their upstream usage documentation is at
<https://mini-swe-agent.com>.

## Lineage

This package retains code derived from mini-swe-agent. Preserve the upstream MIT notice in
`LICENSE.md`; see [../NOTICE.md](../NOTICE.md) and [../docs/LICENSES.md](../docs/LICENSES.md).

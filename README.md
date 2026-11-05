# VeraAgent

**English** | [简体中文](README_zh-CN.md)

VeraAgent is a local, single-user AI agent workstation for software projects.
It puts a project task board, a main Agent conversation, subagents, multi-agent
collaboration, and **user-defined workflows and organization structures** in one
desktop app. You design a workflow or an organization template once, instantiate
it inside a project, and invoke it from a conversation.

The agent core is derived from [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
and follows the minimal-tool philosophy of Pi Agent (four primitives: read, write, edit,
bash). This describes lineage; it does not imply endorsement by either project.

The [project website](website/README.md) introduces the desktop interface, system design,
and practical documentation. Its interface illustrations are static examples.

## Features

- **Projects**: bind local folders and chat with an Agent in the project context
  (the project's `AGENTS.md` rules are included when enabled in settings).
- **Task board**: track project work items (backlog → done) and link them to conversations.
- **Subagents**: the main Agent can delegate research and review to isolated subagents.
- **Workflows and organizations**: build templates in a visual editor (agents, YES/NO
  conditions, loops), instantiate them per project with a goal and background, and run
  them from chat with explicit confirmation. Each node runs in its own session; results
  return to the originating conversation after a Supervisor review.
- **Tools**: file explorer, diff/stage/checkpoint, Git branches, terminal, MCP servers,
  Skills, scheduled prompts, and usage analytics.
- **Evaluation and learning**: every turn is traced and scored locally; scoped, versioned long-term
  memory with budgeted recall; an eval runner over the real chat pipeline (`vera-eval`); and
  improvement proposals that take effect only after an eval gate and your approval
  ([details](docs/LEARNING_LOOP.md)).
- **Permissions**: per-category approval (edit, terminal, search, MCP, delegation)
  with every tool call shown in the conversation.

VeraAgent is **not** an OS sandbox: terminal commands run as your Windows user.
Bind only trusted projects and review MCP servers and Skills before enabling them.

## Quick start (Windows)

Requirements: Windows 10/11, Git, Node.js 24 LTS (or 20.19+ / 22.12+), Python 3.10+, [uv](https://docs.astral.sh/uv/) 0.11+, and the Microsoft Edge WebView2 Runtime.

```powershell
git clone https://github.com/Felix-0625/Vera-Agent.git
cd Vera-Agent\frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

Then add a model under **设置 → 模型** (the UI is in Chinese). VeraAgent is distributed
as source on GitHub only; there is no npm package, PyPI package, or signed installer.
Details: [Windows installation](docs/INSTALL_WINDOWS.md).

## Runnable examples

Start with the [example index](examples/README.md). Each example includes prerequisites,
commands, expected observations, generated files and cleanup instructions.

| Goal | Example | Provider calls |
| --- | --- | --- |
| Follow template → project instance → confirmed workflow → returned answer | [Workflow quickstart](examples/workflow-quickstart/README.md) | None for setup/dry run; paid model for the desktop run |
| Verify scoped memory, version restore and a real eval acceptance command | [Learning loop](examples/learning-loop/README.md) | None for the scripted check; optional paid single-case CLI run |
| Connect two inspectable read-only tools over real MCP stdio | [MCP server](examples/mcp-server/README.md) | None |

For the offline examples, first install the [development dependencies](docs/DEVELOPMENT.md),
then run from the repository root:

```powershell
.\vera-agent\.venv\Scripts\python.exe examples\workflow-quickstart\setup_demo.py --dry-run
.\vera-agent\.venv\Scripts\python.exe examples\learning-loop\verify.py
.\vera-agent\.venv\Scripts\python.exe examples\mcp-server\test_client.py
```

These exercise real local APIs, tools/storage or MCP transport with synthetic inputs.
The eval example labels its model as scripted; passing it does not measure provider quality
or prove that an improvement proposal helps. Live model steps are explicit and excluded from CI.

## How it works

```text
pywebview window (WebView2)
  └── React + TypeScript UI  (frontend/)
        │  HTTP / SSE / WebSocket on 127.0.0.1
        ▼
      Starlette API  (vera-agent/src/vera_agent/server/)
        ├── chat stream → Agent loop → model (LiteLLM) → tools
        ├── projects, threads, task board (SQLite), workflows/runs (JSON)
        └── files, Git, terminal, MCP, Skills
```

See [Architecture](docs/ARCHITECTURE.md) for the module map and request flow.

## Repository layout

```text
frontend/       React UI (Vite). See frontend/README.md
vera-agent/     Python package: agent loop, tools, sessions, local API, desktop shell
examples/       Runnable examples (start with workflow-quickstart/)
tests/          Repository-level tests and check-all.ps1 (backend/frontend tests live next to their code)
docs/           Maintainer and user documentation
scripts/        Maintenance scripts (API index, license inventory)
website/        Static project website (introduction, design, documentation)
```

## Documentation

| Topic | Document |
| --- | --- |
| Install and update | [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md) |
| Development setup and conventions | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [CONTRIBUTING.md](CONTRIBUTING.md) |
| Architecture and module map | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| HTTP API reference | [docs/API.md](docs/API.md) |
| Memory, traces and improvement request/response contracts | [docs/LEARNING_API.md](docs/LEARNING_API.md) |
| Data model and local storage | [docs/DATA_MODEL.md](docs/DATA_MODEL.md) |
| Configuration and environment variables | [docs/CONFIGURATION.md](docs/CONFIGURATION.md) |
| Tools, permissions, MCP, Skills | [docs/TOOLS_AND_MCP.md](docs/TOOLS_AND_MCP.md) |
| Evaluation and self-improvement (RSI) | [docs/EVAL_AND_RSI.md](docs/EVAL_AND_RSI.md) |
| Traces, memory, configuration files | [docs/LEARNING_LOOP.md](docs/LEARNING_LOOP.md) |
| System diagrams and editable source | [website/diagrams/README.md](website/diagrams/README.md) |
| Testing and verification records | [docs/TESTING.md](docs/TESTING.md), [tests/README.md](tests/README.md) |
| Website and deployment | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [website/README.md](website/README.md) |
| Licenses | [docs/LICENSES.md](docs/LICENSES.md) |

## Verify a checkout

```powershell
./tests/check-all.ps1
```

Runs lint, backend tests, repository tests (examples, docs, hygiene), the MCP example,
the website checker, frontend lint, unit tests, and the production build. It does not
install dependencies or call model APIs.

Python uses Ruff; the frontend uses strict TypeScript, Oxlint and Prettier. CI checks
formatting and source size. Self-authored code (including tests, CSS and website scripts)
has a hard 1000-line file limit; runtime modules target 450 lines, with documented existing
exceptions that may only shrink. Dependency locks and upstream vendor assets are exempt.

## Status

VeraAgent is alpha software under active development, built for Windows. The
documentation describes current behavior and known limits; see [docs/TESTING.md](docs/TESTING.md).

## License

MIT, see [LICENSE](LICENSE). `vera-agent/` contains code derived from mini-swe-agent;
its MIT notice is preserved in [vera-agent/LICENSE.md](vera-agent/LICENSE.md). See
[NOTICE.md](NOTICE.md) and the [third-party license inventory](docs/THIRD_PARTY_LICENSES.md).

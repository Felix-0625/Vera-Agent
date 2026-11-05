# Tests

VeraAgent keeps tests next to the code they exercise and uses this folder for
repository-level checks and the single entry point that runs everything.

| Layer | Location | Runner | What it covers |
| --- | --- | --- | --- |
| Backend unit/API | `vera-agent/tests/` | pytest | Agents, models, tools, sessions, every API route group (server/), workflow runs, task board |
| Frontend unit | `frontend/src/**/*.test.ts` | Vitest | Pure logic and frontend/backend contracts (e.g. model provider allow-list) |
| Repository | `tests/` (this folder) | pytest | Examples run without paid providers, docs links resolve, API parameters are independently checked, env vars documented, no secrets/residue, lockfiles tracked, comments in English; all own-code files ≤1000 lines |
| MCP example | `examples/mcp-server/test_client.py` | Python | Real MCP stdio handshake with the sample server |
| Website | `website/check_site.py` | Python | Pages, local links, anchors, assets |

## Run everything

From the repository root on Windows (after the setup in [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)):

```powershell
./tests/check-all.ps1
```

It stops at the first failure, does not install dependencies, and never calls a model API.

The frontend step checks Prettier formatting, strict TypeScript, unused symbols, Oxlint,
Vitest and the production build. The workflow example checks repeat setup and isolated state;
the learning example uses a scripted provider with real tools, acceptance commands and memory storage.

## Run one layer

```powershell
vera-agent\.venv\Scripts\python.exe -m pytest tests          # repository checks
cd vera-agent; .\.venv\Scripts\python.exe -m pytest tests     # backend
cd frontend; npm test                                         # frontend
```

## Writing tests

- Put a test at the layer that owns the behavior; name files after the behavior
  (`test_taskboard.py`, `codeEditorUtils.test.ts`), not after a development phase.
- Use pytest (not unittest). Each test module starts with a one-line docstring saying what it covers.
- API tests use `starlette.testclient.TestClient(create_app(repo_root=tmp_path))` so data
  goes to a temporary directory. A `conftest.py` fixture lets the default `testserver`
  host pass the loopback check; standalone scripts need `base_url="http://127.0.0.1"`.
- Do not call live model providers. Tests that need public network services are
  skipped unless `VERA_RUN_NETWORK_TESTS=1`; real-provider "fire" tests need `--run-fire`.
- A mock-only test is not evidence that a live provider or external MCP server works;
  record such manual checks in [docs/TESTING.md](../docs/TESTING.md).

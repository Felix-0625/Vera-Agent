# Testing and verification

## Existing test layers

The backend suite lives in `vera-agent/tests/` and is organized around API/server, agents, configuration, environments, models, sessions, tools, and integration behavior. Tests for optional ConTree and Modal adapters are skipped when their extras are not installed.

The frontend currently has TypeScript/Vite build and Oxlint checks, but no dedicated React component test runner in `frontend/package.json`. A successful production build checks compilation and bundling; it does not prove that every screen or backend interaction behaves correctly.

The sample MCP server has an official-SDK stdio client smoke check under `examples/mcp-server/test_client.py`. It performs a real local handshake, checks tool discovery, and exercises the fixed read-only fixture. It is separate from the backend pytest suite and does not test VeraAgent's MCP settings UI or arbitrary external servers.

## Run checks

On Windows, from the repository root:

```powershell
./tests/check-all.ps1
```

Individual commands:

```powershell
cd vera-agent
python -m pytest tests
cd ..\frontend
npm run lint
npm run build
cd ..
.\vera-agent\.venv\Scripts\python.exe examples\mcp-server\test_client.py
```

The top-level script stops on the first failing command and prints each stage. It does not call model APIs or install dependencies. The web-search/fetch integration test is skipped unless `VERA_RUN_NETWORK_TESTS=1` is set; that opt-in test makes real requests to public services.

## What these checks do not prove

- Mock model tests do not prove compatibility with every provider or that a key is valid.
- API tests do not prove the Windows pywebview picker, WebView2 runtime, or installer works on a clean machine.
- A workflow template saved in storage does not prove a full workflow run, visible stage trace, and result return path.
- MCP protocol smoke tests do not certify a package’s safety.
- Passing tests do not establish performance or benchmark results. Publish only measured results with the exact dataset, command, and environment.

For a release candidate, also perform a clean Windows install, a real configured-model conversation, project binding, file operation permission checks, one tool call, one MCP call, one Skill activation, and an update/backup check. Record model/provider and whether any external service was used.

## Workflow and Task Board acceptance (2026-10-16)

This acceptance covered the current workflow/architecture editor changes and the embedded Task Board frontend/backend contract.

| Area | Verification | Result |
| --- | --- | --- |
| Workflow and architecture APIs | Full backend suite, including isolated workflow context, strict control decisions, run/node state transitions, bounded provenance, and persisted results | 650 passed, 81 skipped |
| Workflow editor | Opened a saved project workflow in the browser; confirmed the editor loaded its four nodes and three edges, pointer/hand canvas controls, port legend, and editable definition fields | Passed for editor loading and presentation |
| Workflow execution | Ran a real branch workflow: start node → YES/NO decision → YES worker → Supervisor; then ran a two-stage architecture serially. Both returned results to the originating chat. After observing ambiguous duplicate stage labels, changed the run log to label control and Supervisor calls by stage, then reran the branch workflow | Passed for branch selection, serial architecture handoff, visible stage trace, and result return |
| Task Board API | SQLite persistence, project filtering, status/priority/labels, optimistic version conflict, archive filtering, invalid input, and cross-project conversation rejection | Passed |
| Task Board frontend | In the browser, created and edited an item, moved its status through the editor, launched Agent handling on another synthetic item, confirmed the linked conversation and `in_progress` status, then archived test items and confirmed the active board was empty | Passed for create/edit/status/Agent linkage/archive; drag gesture itself was not exercised |
| Frontend/build | Desktop TypeScript/Vite build and Oxlint | Build passed; lint exited 0 with existing React hook/Fast Refresh warnings |
| Python style | Ruff on changed workflow/chat/taskboard routes and their focused API tests | Passed |
| Desktop chain | Restarted with `start-desktop.ps1` after the final frontend build; the pywebview process launched and `/api/topology` returned HTTP 200 | Passed |

The Task Board test items were archived and are excluded from normal board listings; the synthetic Agent verification conversation remains in the test project history for inspection. The current temporary DeepSeek credential passed the model connection test and was used for the synthetic workflow/Task Board calls. Drag gesture itself was not exercised. This record accepts the tested interaction paths; it is not a clean-machine installer or release certification.

## Release-preparation verification (2026-10-17)

| Area | Verification | Result |
| --- | --- | --- |
| Backend | `tests/check-all.ps1` on Windows/Python 3.14.5 | 656 passed, 81 skipped, 3 warnings |
| MCP example | Official SDK stdio handshake, tool discovery, and four read-only fixture calls | Passed |
| Frontend | Oxlint and production TypeScript/Vite build | Passed |
| Website | Static route, asset, and anchor checker | Passed for all three pages |
| Locked installs | `uv lock --check`; clean temporary `npm ci --ignore-scripts` from `frontend/package-lock.json` | Passed |
| License inventory | Clean temporary Windows desktop runtime environment plus all npm lockfile entries | 98 Python packages and 92 npm lockfile packages; no unknown license metadata |
| npm package | `npm publish --dry-run --access public --registry=https://registry.npmjs.org` | Passed; tarball contained five expected files. No publication occurred. |
| Workflow files | `actionlint` 1.7.12 and YAML parsing for CI, npm publish, Pages deploy, and Dependabot; Actions pinned to verified release commit SHAs | Passed locally; GitHub-hosted workflow runs have not been observed |

These checks do not prove a clean-machine Windows install, a public GitHub Pages deployment, npm account ownership, or first publication. The npm package is not registered and its name is not reserved. Review [release limitations](INSTALL_WINDOWS.md) and [license provenance](LICENSES.md) before claiming public-release readiness.

## Release-preparation follow-up (2026-10-18)

| Area | Verification | Result |
| --- | --- | --- |
| Repository checks | `./tests/check-all.ps1` | Passed: 681 passed, 56 skipped, 3 warnings; Python naming lint, MCP stdio smoke, website checker, frontend lint, and production build passed |
| Clean Windows desktop dependencies | `uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.12` into a fresh temporary environment, followed by importing VeraAgent, pywebview, and uvicorn | Passed; 99 locked packages resolved, 98 runtime distributions inventoried |
| Minimum Python runtime | Fresh `uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.10` environment and imports for VeraAgent, pywebview, and uvicorn | Passed on CPython 3.10.20; 103 locked packages installed |
| Frontend clean install | Copied tracked frontend sources without `node_modules` or `dist` into a new temporary directory and ran `npm ci` | Passed; 49 packages installed, npm audit reported 0 vulnerabilities |
| Frontend clean build | `npm run lint` and `npm run build` in that clean directory | Passed; Oxlint exited 0 and TypeScript/Vite production build completed |
| License inventory | Regenerated from clean Python 3.10 and 3.12 Windows desktop environments plus `frontend/package-lock.json` | Passed; 200 Python rows across both runtime versions and 92 npm package rows, no unknown license metadata |

The temporary verification environment and frontend copy are local build artifacts, not tracked repository content. These results verify reproducible dependency installation and frontend compilation; they do not replace a clean-machine desktop launch or external GitHub/npm account setup.

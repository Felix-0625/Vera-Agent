# Testing and verification

## Test layers

| Layer | Location | What it covers |
| --- | --- | --- |
| Backend | `vera-agent/tests/` | API routes (`server/`), agents, configuration, environments, models, sessions, tools, multi-agent flows. Optional ConTree/Modal adapter tests are skipped without their extras. |
| Chat turn characterization | `vera-agent/tests/server/test_chat_stream_events.py` | The ordered SSE event sequence of a turn (plain reply, tool call, approve, reject, `O:` correction, interrupt during approval, tool limit, model error). Any refactor of `run_turn` must keep these passing. |
| Learning loop | `vera-agent/tests/telemetry/`, `memory/`, `evals/`, `evolution/` | Scoring rules, trace store, secret redaction, scoped/versioned memory and Chinese recall, consolidation, the eval runner over the real pipeline with scripted models and real acceptance scripts, the gate, and the full failure → proposal → gate → adoption → online gain → rollback path. No model API is called. |
| Frontend | `frontend/src/**/*.test.ts` (Vitest) | Pure logic and frontend/backend contracts. There are no React component/DOM tests yet; the TypeScript build checks compilation, not screen behavior. |
| Repository | `tests/` | Workflow quickstart dry run through the real API, template validity, Markdown links, API index freshness, env-var documentation, secrets/residue, tracked lockfiles, English comments, LF storage. |
| MCP example | `examples/mcp-server/test_client.py` | Real stdio handshake, tool discovery, and the read-only fixture. It does not test the MCP settings UI or third-party servers. |
| Website | `website/check_site.py` | Page entry points, local links, anchors, assets. |

See [tests/README.md](../tests/README.md) for conventions.

## Run checks

On Windows, from the repository root:

```powershell
./tests/check-all.ps1
```

Individual commands:

```powershell
cd vera-agent
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\python.exe -m pytest tests
cd ..
.\vera-agent\.venv\Scripts\python.exe -m pytest tests
.\vera-agent\.venv\Scripts\python.exe examples\mcp-server\test_client.py
cd frontend
npm run lint
npm run format:check
npm test
npm run build
```

The top-level script stops on the first failing command. It does not call model APIs or install dependencies. Web-search/fetch integration tests are skipped unless `VERA_RUN_NETWORK_TESTS=1`; real-provider tests require `--run-fire`.

## What these checks do not prove

- Mock model tests do not prove compatibility with every provider or that a key is valid.
- API tests do not prove the Windows pywebview picker, WebView2 runtime, or first launch from a clean checkout.
- A workflow template saved in storage does not prove a full workflow run, visible stage trace, and result return path.
- MCP protocol smoke tests do not certify a package’s safety.
- Passing tests do not establish performance or benchmark results. Publish only measured results with the exact dataset, command, and environment.
- The learning-loop tests use scripted models. They prove the runner, gate and adoption logic, not that a real model improves; that needs `vera-eval run` with a configured model (it costs money and is never part of `check-all.ps1`).

## Source standardization verification (2026-11-02)

This pass covered source organization, documentation and reproducible examples in the local
working tree. It did not publish a release or run paid model evaluations.

- Backend regression: **788 passed, 81 skipped**, with the existing Pydantic `ReadOnly` warning.
  The test count is preserved after splitting the large interactive-agent and frontend API suites.
- Repository checks: **48 passed**, including repeatable workflow setup, the scripted-provider
  learning example, independent API query assertions and the hard 1000-line own-code limit.
- Frontend: **46 tests passed**; strict TypeScript and unused-symbol checking are enabled.
  The added chat-store checks cover stale streaming/history responses and per-conversation queues.
- Python Ruff, frontend Oxlint, Prettier and the browser production build passed.
- The three documented example commands were executed: workflow dry run, memory/eval verification,
  and MCP stdio discovery plus four read-only calls. No paid provider requests were made.
- Isolated browser smoke operations switched workflow type, created/renamed a node, saved the
  template and checked the persisted result. Site home/design/docs loaded without script errors,
  broken images or horizontal overflow at the tested desktop size.
- The split stylesheets were compared structurally with their original ordered CSS rules;
  application design tokens and base styles were also checked in the browser.

Browser smoke coverage is narrower than a full desktop/provider acceptance run. The historical
records below describe their own dates and scopes and should not be treated as newer measurements.

For a release candidate, also perform a clean Windows install, a real configured-model conversation, project binding, file operation permission checks, one tool call, one MCP call, one Skill activation, and an update/backup check. Record model/provider and whether any external service was used.

## Pre-push verification (2026-10-27)

| Check | Result |
| --- | --- |
| Full backend suite (`python -m pytest tests`) | 800 passed, 69 skipped; one existing Pydantic `ReadOnly` warning |
| Repository tests | 39 passed: docs/links, generated API index, examples, source size and hygiene |
| Frontend | 44 tests passed; Oxlint and TypeScript/Vite web and desktop production builds passed |
| Python style | Backend and repository Ruff lint/format checks passed |
| MCP example | Stdio handshake, tool discovery, and four read-only calls passed |
| Static website | Four page entry points and assets passed validation |
| Dependency lock | `uv lock --check --offline` passed |
| Browser | Chinese/English design pages each loaded five diagrams; twelve desktop/mobile route checks and ten SVG bounds checks passed; no page script errors |

The regression suite includes the last acceptance issue: `python -m pytest -q --version`
must not overwrite an earlier failed verification score. This pass did not call a real model,
record a new product video, trigger hosted CI, or deploy the website. The recording plan from that historical pass is [archived](archive/DEMO_RECORDING.md); the current website no longer includes the video/playground. Runnable examples are in [examples/](../examples/README.md).
Editable diagrams and SVG exports are indexed in [the diagram library](../website/diagrams/README.md).

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

Task Board test items were archived after the run. The temporary provider credential passed a connection check and was used for synthetic workflow and Task Board calls. Drag gesture itself was not exercised. This record accepts the tested interaction paths; it is not a clean-machine first-launch or release certification.

## Release-preparation verification (2026-10-17)

| Area | Verification | Result |
| --- | --- | --- |
| Backend | `tests/check-all.ps1` on Windows/Python 3.14.5 | 656 passed, 81 skipped, 3 warnings |
| MCP example | Official SDK stdio handshake, tool discovery, and four read-only fixture calls | Passed |
| Frontend | Oxlint and production TypeScript/Vite build | Passed |
| Website | Static route, asset, and anchor checker | Passed for all three pages |
| Locked installs | `uv lock --check`; clean temporary `npm ci --ignore-scripts` from `frontend/package-lock.json` | Passed |
| License inventory | Clean temporary Windows desktop runtime environment plus all npm lockfile entries | 98 Python packages and 92 npm lockfile packages; no unknown license metadata |
| Workflow files | `actionlint` 1.7.12 and YAML parsing for CI, Pages deploy, and Dependabot; Actions pinned to verified release commit SHAs | Passed locally; GitHub-hosted workflow runs have not been observed |

These checks do not prove a clean-machine Windows desktop launch or a public GitHub Pages deployment. Review [installation limitations](INSTALL_WINDOWS.md) and [license provenance](LICENSES.md) before claiming distribution readiness.

## Release-preparation follow-up (2026-10-18)

| Area | Verification | Result |
| --- | --- | --- |
| Repository checks | `./tests/check-all.ps1` | Passed: 681 passed, 56 skipped, 1 upstream Pydantic warning; Python naming lint, MCP stdio smoke, website checker, frontend lint, and production build passed |
| Clean Windows desktop dependencies | `uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.12` into a fresh temporary environment, followed by importing VeraAgent, pywebview, and uvicorn | Passed; 99 locked packages resolved, 98 runtime distributions inventoried |
| Minimum Python runtime | Fresh `uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.10` environment and imports for VeraAgent, pywebview, and uvicorn | Passed on CPython 3.10.20; 103 locked packages installed |
| Frontend clean install | Copied tracked frontend sources without `node_modules` or `dist` into a new temporary directory and ran `npm ci` | Passed; 49 packages installed, npm audit reported 0 vulnerabilities |
| Frontend clean build | `npm run lint` and `npm run build` in that clean directory | Passed; Oxlint exited 0 and TypeScript/Vite production build completed |
| License inventory | Regenerated from clean Python 3.10 and 3.12 Windows desktop environments plus `frontend/package-lock.json` | Passed; 200 Python rows across both runtime versions and 92 npm package rows, no unknown license metadata |
| Desktop startup with port collision | Ran `start-desktop.ps1` while 8000–8002 were occupied by unrelated services; inspected the VeraAgent WebView and its API traffic | Passed; launcher selected port 8003, built the desktop bundle with that API URL, and loaded projects, model settings, groups, conversations, and context status |

The temporary verification environment and frontend copy are local build artifacts, not tracked repository content. These results verify reproducible dependency installation and frontend compilation; they do not replace a clean-machine desktop launch or an actual GitHub Pages deployment.

## Open-source preparation (2026-10-18)

| Area | Verification | Result |
| --- | --- | --- |
| Repository checks | `./tests/check-all.ps1` on Windows | Passed: backend ruff lint/format; 656 passed, 81 skipped; repository tests 29 passed; MCP stdio smoke; website checker; Oxlint; Vitest 25 passed; production build |
| Workflow quickstart | `examples/workflow-quickstart/setup_demo.py --dry-run` against an in-process app | Passed: project bind, two templates, workflow instance, task board item, and a `ready` run with 5 nodes created through public routes; no model call |
| Lockfile | `uv lock --check` with `vera-agent/uv.lock` no longer Git-ignored | Passed (181 packages) |

Not verified in this round: a live model conversation, an executed workflow run in the desktop UI, a clean-machine install from a fresh clone, and hosted GitHub Actions runs. `docs/THIRD_PARTY_LICENSES.md` was not regenerated after adding Vitest as a frontend dev dependency.

## Live end-to-end acceptance (2026-10-18)

Run against a separate API instance (`create_app(repo_root=<temporary data root>)`) with a real DeepSeek model profile, temporary Git projects, and the Vite dev UI in a browser. Each row used real model calls unless marked otherwise.

| Area | Verification | Result |
| --- | --- | --- |
| Projects and history | Bind two folders, rename/pin, unbind (folder kept on disk), reject a missing path; thread search, pin, replay, delete | Passed |
| Settings | Legacy permissions normalized; invalid mode/provider rejected; model connection test; user rules, `AGENTS.md`, and user memory reflected in answers | Passed |
| Tools and approvals | `read` tool; `edit` asked for approval, rejection left the file unchanged, approval applied it; multi-turn recall of the change | Passed |
| Subagents | Explicit reviewer and researcher requests dispatched to the right role; main agent summarized both reports; progress events coalesced (5 instead of 84) | Passed |
| Side chat | Answered from supplied main-conversation context; not persisted | Passed |
| Context compaction | 14 turns on a 12k-token window: 4 compactions, all 8 planted facts recalled, full transcript kept | Passed |
| Subagent rebirth | Session at 118% of the window after 3 prior compactions: rebirth to 23%, key facts kept in the checkpoint, transcript kept (model call real; earlier compactions simulated) | Passed |
| Workflow (UI) | Invoked from chat → analyst → reviewer → YES/NO condition → only the NO branch ran, YES branch skipped → Supervisor → answer delivered to the originating chat | Passed |
| Loop control | Loop decision returned NO with feedback for a failing draft and YES for a passing one; control decision on a non-control node rejected (409) | Passed |
| Organization | Lead → implementer and tester (each received the lead output) → Supervisor → delivered; via API and via the UI | Passed |
| Task board | Create, link conversation, stale `version` rejected (409), invalid status rejected, project isolation, archive | Passed |
| Scheduled task | One-time task fired by the scheduler, replied, `last_status=success`; past time rejected; toggle and delete | Passed |
| MCP | `examples/mcp-server` registered, attached to a chat, `list_tasks` called, answer used the result | Passed |
| Skill | Install, attach (instruction applied), disabled Skill rejected when attached (409) | Passed |
| UI panels | Right sidebar: files, diff, terminal, GitFlow, metrics, subagents, side chat, workflow; settings: models, permissions, MCP, Skills, rules/memory | All loaded with live data |

Defects found and fixed during this run, each with a regression test: template syntax in goals/rules/Skills broke the turn (`'goal' is undefined`); scheduled tasks read model settings from the project instead of the application root; MCP results were lost after the chat-route refactor; the Supervisor review overwrote the last node's run record; run events ended with a node event after `completed`; "审查子智能体" was routed to the researcher; bash actions had an empty tool name; subagent progress flooded the stream; the rebirth message over-counted compactions; threads streamed without creation kept a `Thread th_…` title.

Follow-up checks in the same round:

| Area | Verification | Result |
| --- | --- | --- |
| Fresh checkout | Copied exactly the files Git would commit into an empty folder, ran `npm ci`, `uv sync --locked --extra desktop --extra dev`, and `./tests/check-all.ps1` | Passed after tracking the `tests/test_data/*.traj.json` fixtures, which an ignore rule had excluded (677 passed, 81 skipped; repository 36; Vitest 33; build) |
| CI commands | The `ci.yml` backend steps (`uv run --locked` ruff, pytest, repository tests, MCP example) in that folder; `actionlint` 1.7.12 on both workflows | Passed; no workflow findings |
| Desktop shell | `start-desktop.ps1` on the refactored code: frontend build, backend on port 8000, pywebview window titled VeraAgent, real project list served, API keys not exposed; window closed and backend stopped by the launcher | Passed |
| New conversation in project | Trusted (OS-level) click on the sidebar "+" in Chromium | Passed: draft bound to the project and the composer shows it; the earlier failure came from the preview tool's synthetic click |
| Startup directory | API started without `repo_root` no longer adds its working directory to project history | Fixed with a regression test; existing history entries are unchanged and can be removed in the UI |

Not verified: hosted GitHub Actions runs and an install on a separate machine. Model compliance with Skill instructions and the memory policy is not guaranteed.

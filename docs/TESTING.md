# Testing and verification

## Existing test layers

The backend suite lives in `vera-agent/tests/` and is organized around API/server, agents, configuration, environments, models, sessions, tools, and integration behavior. The current checkout contains 71 test files; this is a file count, not a pass rate or coverage claim. Tests for optional ConTree and Modal adapters are skipped when their extras are not installed.

The frontend currently has TypeScript/Vite build and Oxlint checks, but no dedicated React component test runner in `frontend/package.json`. A successful production build checks compilation and bundling; it does not prove that every screen or backend interaction behaves correctly.

The sample MCP server has a stdio JSON-RPC client smoke test under `examples/mcp-server/test_client.py`. It is separate from the backend pytest suite.

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
```

The top-level script stops on the first failing command and prints each stage. It does not call model APIs or install dependencies. The web-search/fetch integration test is skipped unless `VERA_RUN_NETWORK_TESTS=1` is set; that opt-in test makes real requests to public services.

## What these checks do not prove

- Mock model tests do not prove compatibility with every provider or that a key is valid.
- API tests do not prove the Windows pywebview picker, WebView2 runtime, or installer works on a clean machine.
- A workflow template saved in storage does not prove a full workflow run, visible stage trace, and result return path.
- MCP protocol smoke tests do not certify a package’s safety.
- Passing tests do not establish performance or benchmark results. Publish only measured results with the exact dataset, command, and environment.

For a release candidate, also perform a clean Windows install, a real configured-model conversation, project binding, file operation permission checks, one tool call, one MCP call, one Skill activation, and an update/backup check. Record model/provider and whether any external service was used.

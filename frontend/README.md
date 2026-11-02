# VeraAgent frontend

React 19 + TypeScript + Vite UI for the VeraAgent desktop workstation. It is
rendered inside a pywebview/WebView2 window by `vera_agent.desktop`, or in a
browser during development, and talks to the local Python API over loopback.

## Scripts

Run from `frontend/` after `npm ci`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server on <http://localhost:5173>; proxies `/api` (HTTP and WebSocket) to the backend |
| `npm run build` | Type-check (`tsc -b`, including tests) and build `dist/` for the browser |
| `npm run build:desktop` | Same, with `--mode desktop`: relative asset paths and an absolute API URL |
| `npm run lint` | Oxlint (`.oxlintrc.json`) |
| `npm run format` / `npm run format:check` | Apply/check Prettier formatting; CI runs the check |
| `npm test` | Vitest unit tests (`src/**/*.test.ts`) |
| `npm run test:watch` | Vitest in watch mode |

Start the backend for `npm run dev` from `vera-agent/`:

```powershell
uv run uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000
```

## API base URL

`vite.config.ts` injects `import.meta.env.VITE_API_BASE_URL`:

| Mode | Value | Used by |
| --- | --- | --- |
| dev / browser build | `VITE_API_BASE_URL` or empty (same origin; Vite proxies `/api` to `VITE_API_PROXY_TARGET`, default `http://127.0.0.1:8000`) | `npm run dev`, `npm run build` |
| desktop | `VITE_API_BASE_URL` or `http://127.0.0.1:8000` | `npm run build:desktop`; `start-desktop.ps1` sets the chosen port |

All HTTP calls go through `request()` in `src/api/client.ts`.

## Source map

```text
src/
├── api/          HTTP/SSE clients, one file per backend domain (see docs/API.md)
├── components/
│   ├── common/   Shared controls: Button, Field, Modal, Switch, RadioGroup, ...
│   ├── composer/ Center workspace: message stream, input card, approval banner, model picker
│   ├── dialogs/  Modal dialogs: settings tabs, model config, project selector, scheduled tasks
│   ├── layout/   Workspace shell and resize handles
│   ├── sidebar/  Left navigation: projects, conversations, pinned items
│   └── tools/    Right-side tool panels: files, diff, terminal, Git, workflow, task board, MCP, Skills
│                 (workflowRunner.ts holds the workflow/organization run scheduler, tested in Node)
├── stores/       zustand stores (state shapes are documented at the top of each file)
├── styles/       tokens.css and ordered global/ stylesheet modules imported by globals.css
├── types/        TypeScript mirrors of backend JSON (snake_case field names kept as-is)
├── App.tsx       Root layout
└── main.tsx      Entry point
```

### State

| Store | Holds |
| --- | --- |
| `chatStore` | Threads, active messages, streaming/approval state, prompt queue, selected model |
| `projectStore` | Current project, project history, groups |
| `layoutStore` | Theme, sidebar sizes, per-conversation right sidebar layout, open dialogs |
| `toolTabsStore` | Right-side tool tabs per conversation |
| `sideChatStore` | Ephemeral side chats (not persisted) |
| `terminalStore` | Terminal WebSocket connection and output |
| `filePreviewStore` | Open file preview per project |
| `orchestrationInvokeStore` | Workflow runs requested from chat, waiting for the workflow panel |

## Conventions

- Components and their files are `PascalCase` (`TaskboardTab.tsx`); hooks are `useX`;
  other modules are `camelCase` (`codeEditorUtils.ts`); CSS files are `kebab-case`.
  `main.tsx` (Vite convention) and `toolLauncherData.tsx` (a data table with JSX icons) are intentional exceptions.
- Use design tokens from `styles/tokens.css` (`var(--text-primary)`, `var(--space-2)`, ...) instead of hard-coded colors.
- UI copy is Chinese by design; code comments are English.
- TypeScript `strict` is enabled. Keep JSX readable with Prettier; split responsibilities
  instead of compressing code to satisfy size checks. Workflow controllers, views, canvas
  and node components are separate modules; `WorkflowTab.tsx` remains the public entry.
- Keep request/response types in `src/types/` aligned with the backend route and update
  [docs/API.md](../docs/API.md) when a contract changes.

### Adding a right-side tool tab

1. Add the id to `ToolTabId` in `src/types/tool.ts`.
2. Add a launcher entry to `TOOL_LAUNCHER_ITEMS` in `components/tools/toolLauncherData.tsx`.
3. Render the panel in the `renderTool` switch of `components/tools/RightToolsContainer.tsx` (lazy-load with `Suspense` like the others).

### Adding an API call

1. Add or extend the type in `src/types/`.
2. Add a typed function in the matching `src/api/*.ts` file using `request()`.
3. Run `python scripts/generate_api_index.py` from the repository root if a backend route was added.

## Testing

Unit tests live next to the code (`foo.ts` → `foo.test.ts`) and run in Node. They
cover pure logic and contracts, for example that `MODEL_PROVIDERS` matches the
backend provider allow-list. There are no component/DOM tests yet; UI behavior is
verified manually (see [docs/TESTING.md](../docs/TESTING.md)). Development setup is in
[docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).

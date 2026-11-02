# Contributing

VeraAgent is under active development. Small, reviewable changes with reproducible evidence are easiest to maintain.

## Before submitting

1. Describe the user-visible behavior or defect and the affected backend/frontend contract.
2. Keep project data and credentials out of commits. Runtime files belong under `.agents/`, which is ignored.
3. Add or update tests at the layer that owns the behavior (see [tests/README.md](tests/README.md)). Do not use a mock-only test as evidence of a live provider or external MCP integration.
4. Run `./tests/check-all.ps1` on Windows, or the individual commands in [docs/TESTING.md](docs/TESTING.md).
5. Explain important behavior changes, migration effects, and any verification you could not run.

## Code conventions

### Python (`vera-agent/src/vera_agent`, `tests/`, `scripts/`, `examples/`)

- `snake_case` modules, functions, and variables; `PascalCase` classes; `UPPER_SNAKE_CASE` constants. Private helpers start with `_`.
- Type annotations on public functions; `pathlib.Path` over `os.path`.
- Ruff enforces lint, import order, naming (`N`), and formatting: `ruff check` and `ruff format --check`
  (backend settings in `vera-agent/pyproject.toml`, repository-level settings in `ruff.toml`).
  Exception classes whose names are persisted as exit statuses may carry a documented `N818` exemption.
- Every module starts with a docstring stating its responsibility. Route modules list the routes they own and where they persist data.
- Re-exported names are declared in `__all__`; do not rely on "unused" imports.

### TypeScript (`frontend/src`)

- React components and their files are `PascalCase`; hooks are `useX`; other modules `camelCase`; CSS files and classes `kebab-case`.
- API types in `frontend/src/types` mirror backend JSON and keep `snake_case` field names.
- Use design tokens from `styles/tokens.css` and shared components from `components/common` instead of hard-coded styles.
- Oxlint must pass (`npm run lint`).
- Keep strict TypeScript enabled and run `npm run format:check` (Prettier). Do not compress
  JSX or statements to satisfy line limits; split controller hooks and views by responsibility.

### Size limits

`tests/test_code_size.py` caps files at 450 lines and Python functions at 120 lines. A few existing
modules are listed with their current size as a ceiling; those may only shrink. Split new code by
responsibility instead of raising a limit (see `server/chat/` for the pattern).

Every self-authored code file, including tests, CSS, scripts and website code, also has a
hard 1000-line limit. Generated dependency locks and upstream vendor assets are excluded.
Examples must be reproducible, use synthetic fixtures, state provider costs and generated
files, and document repeat/cleanup behavior. Keep their no-provider checks in repository CI.

### Comments and language

- Source comments and docstrings are in **English**. Explain non-obvious constraints and decisions, not the next line.
- UI copy and built-in prompt templates are Chinese product content and stay in Chinese.
- Maintainer documentation is in English; `README_zh-CN.md` is the Chinese entry point.

### Contracts

- Keep request/response fields aligned between `server/routes`, `frontend/src/api`, and `frontend/src/types`.
- After adding or changing a route, run `python scripts/generate_api_index.py` and update the prose in [docs/API.md](docs/API.md).
- Document environment variables in [docs/CONFIGURATION.md](docs/CONFIGURATION.md) and `.env.example`.

## Commit messages

Use a type prefix: `feat`, `fix`, `docs`, `test`, `ref`, `chore`, `ci`, optionally with a scope (`fix(taskboard): ...`).

## Pull requests

Keep each pull request focused. Include the exact commands run and their results. Do not include real API keys, user `.agents` state, downloaded market packages, logs, or generated build directories.

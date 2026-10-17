# Contributing

VeraAgent is under active development. Small, reviewable changes with reproducible evidence are easiest to maintain.

## Before submitting

1. Describe the user-visible behavior or defect and the affected backend/frontend contract.
2. Keep project data and credentials out of commits. Runtime files belong under `.agents/`, which is ignored.
3. Add or update tests at the layer that owns the behavior. Do not use a mock-only test as evidence of a live provider or external MCP integration.
4. Run `./tests/check-all.ps1` on Windows, or follow the individual commands in [Testing](docs/TESTING.md).
5. Explain important behavior changes, migration effects, and any verification you could not run.

## Code conventions

- Python source is in `vera-agent/src/vera_agent`; use `snake_case` for modules, functions, and variables, and `PascalCase` for classes. Format/lint settings live in `vera-agent/pyproject.toml`.
- React/TypeScript source is in `frontend/src`; use `PascalCase` for React component files and exports, `camelCase` for functions, variables, and hooks (`useThing`), and `kebab-case` for CSS files and classes. Keep shared styles and controls in shared tokens/components rather than page-local hard-coded themes.
- Use English for source-code comments and docstrings. Comments should explain non-obvious constraints or decisions, not paraphrase the next line.
- Keep API request/response fields aligned with `frontend/src/types` and test the route contract when changing it.
- Document runtime configuration in the root README and `.env.example`; update both when environment-variable behavior changes.

## Pull requests

Keep each pull request focused. Include the exact commands run and their results. Do not include real API keys, user `.agents` state, downloaded market packages, logs, or generated build directories.

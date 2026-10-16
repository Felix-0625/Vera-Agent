# Contributing

VeraAgent is under active development. Small, reviewable changes with reproducible evidence are easiest to maintain.

## Before submitting

1. Describe the user-visible behavior or defect and the affected backend/frontend contract.
2. Keep project data and credentials out of commits. Runtime files belong under `.agents/`, which is ignored.
3. Add or update tests at the layer that owns the behavior. Do not use a mock-only test as evidence of a live provider or external MCP integration.
4. Run `./tests/check-all.ps1` on Windows, or follow the individual commands in [Testing](docs/TESTING.md).
5. Explain important behavior changes, migration effects, and any verification you could not run.

## Code conventions

- Python source is in `vera-agent/src/vera_agent`; format/lint settings live in `vera-agent/pyproject.toml`.
- React/TypeScript source is in `frontend/src`; shared styles and controls belong in the shared tokens/components rather than page-local hard-coded themes.
- Keep API request/response fields aligned with `frontend/src/types` and test the route contract when changing it.
- Comments should explain non-obvious constraints or decisions, not paraphrase the next line.

## Pull requests

Keep each pull request focused. Include the exact commands run and their results. Do not include real API keys, user `.agents` state, downloaded market packages, logs, or generated build directories.

# Changelog

## 0.1.0-alpha.1 — 2026-11-06

First public source prerelease for Windows 10/11.

- Local, single-user desktop workspace with project binding, conversations and a task board.
- Multi-agent delegation and editable workflow/organization templates.
- File/Git/terminal tools, approval prompts, MCP and Skills integration.
- Local traces, scoped memory, evaluation and user-approved improvement proposals.
- Bilingual project website, architecture diagrams, locked dependencies and runnable examples.

### Install

See [Windows installation](docs/INSTALL_WINDOWS.md). The downloadable source archive
requires Git, Node.js, Python, uv and WebView2. Configure your own model provider;
provider calls may incur charges. There is no signed installer or automatic updater.

### Known limits

- Alpha software for local Windows use; the public website is documentation, not a hosted Agent.
- Commands run as the Windows user. The app is not an OS sandbox or a multi-user service.
- Automated checks use scripted models and do not establish real-model quality, long-term
  reliability, performance or self-improvement gains.
- Back up application and project `.agents/` data before updating.

Verification results and their evidence boundaries are documented in
[Release verification](docs/RELEASE_0_1_0_ALPHA_1.md) and [Testing](docs/TESTING.md).
The Python version `0.1.0a1` and frontend version
`0.1.0-alpha.1` identify this same prerelease.

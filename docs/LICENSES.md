# Licenses and attribution

## Project code

The repository-root `LICENSE` applies to VeraAgent-authored code unless a file or directory carries a separate notice. `vera-agent/LICENSE.md` preserves the MIT attribution for code derived from mini-swe-agent alongside the VeraAgent contributor notice. The `examples/mcp-server/` sample was written for this repository and is covered by the root MIT license; the MCP Python SDK is a separate dependency with its own license.

## Known third-party components

This is a scoped release review, not a complete Software Bill of Materials (SBOM). The current dependency and asset inspection identified:

| Component or scope | Known license/provenance | Release handling |
| --- | --- | --- |
| Python runtime dependencies | Mixed permissive licenses; `certifi` reports MPL-2.0 in the installed runtime metadata | Include exact versions and notices in a generated release inventory before distribution |
| Optional Python `full`/development environment | Includes SWE-ReX; its dependency tree includes `bashlex` (GPL-3.0-or-later) | The Windows desktop installer uses `uv sync --no-dev --extra desktop` and does not install these optional extras; document this boundary in future package artifacts |
| Frontend runtime dependencies | Lockfile inventory observed MIT, ISC, and BSD-3-Clause packages | Generate and retain a versioned license report for each release build |
| Frontend build dependencies | The lockfile includes Lightning CSS packages under MPL-2.0 | Review the selected notices and distribution implications for the exact release artifact |
| VeraAgent logo source | `VeraLogo.tsx` imports `frontend/src/assets/logo.png`; a matching source image exists at the repository root | The maintainer must confirm ownership or provide the upstream license/provenance before public release |
| Desktop icon and favicon | `frontend/public/logo.ico` is used by the Windows desktop shell; `frontend/public/favicon.svg` is used by the website | Confirm authorship or record the source license before public release |

Dependency licenses above are observations from the current lockfiles and installed metadata, not a complete transitive report. The release inventory must be regenerated from a clean locked install and include exact package versions, license identifiers, and required notices. A top-level MIT license does not relicense third-party material.

## Excluded local checkouts

The ignored `mini-coding-agent/`, `pi-agent/`, and `mcp-sever/` directories are local reference or legacy checkouts and are not included in the Git source tree or package contents. The reproducible MCP example lives in `examples/mcp-server/`.

## Release status

**License review is not complete.** Logo/icon provenance and a clean, versioned transitive dependency inventory remain release blockers. This document is a technical inventory note, not legal advice.

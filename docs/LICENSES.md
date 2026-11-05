# Licenses and attribution

## Project code

The repository-root `LICENSE` applies to VeraAgent-authored code unless a file or directory carries a separate notice. `vera-agent/LICENSE.md` preserves the MIT attribution for code derived from mini-swe-agent alongside the VeraAgent contributor notice. The `examples/` samples were written for this repository and are covered by the root MIT license; the MCP Python SDK is a separate dependency with its own license.

## Known third-party components

The dependency inventory is generated in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) from the locked Windows desktop runtime and frontend lockfile. It records package versions and declared license identifiers; it is not a legal opinion and does not replace review of upstream license texts.

| Component or scope | Known license/provenance | Release handling |
| --- | --- | --- |
| Python runtime dependencies | Mixed licenses; `certifi` reports MPL-2.0 and the inventory lists exact locked versions | Review the recorded license families and required notices for each release |
| Optional Python `full`/development environment | Includes SWE-ReX; its dependency tree includes `bashlex` (GPL-3.0-or-later). The test client uses `httpx2` (BSD-3-Clause) for Starlette's supported TestClient transport. | The source-based desktop install uses `uv sync --no-dev --extra desktop`; these test/benchmark dependencies are not installed for normal desktop use. |
| Frontend dependencies | The lockfile inventory includes runtime and build dependencies, including MPL-2.0-licensed Lightning CSS packages | Review package licenses and preserve required notices when redistributing build artifacts |
| Fonts | No font files are shipped or downloaded. The app UI uses the OS font stack (`-apple-system`, Segoe UI, Roboto, system monospace in `frontend/src/styles/tokens.css`). The website and diagrams name `Inter`, Segoe UI and Microsoft YaHei in CSS/SVG `font-family` lists but declare no `@font-face` and load nothing from a CDN, so a viewer without them falls back to a system font. | Nothing to license or attribute. Adding a bundled font later needs its license (for example Inter is SIL OFL 1.1) kept next to the file. |
| `defusedxml` | PSF license (PSFL); parses user-opened `.xlsx`/`.pptx` XML | Listed in the generated inventory |
| VeraAgent logos and icons | The maintainer confirms `frontend/src/assets/logo.png`, `frontend/public/logo.ico`, and `frontend/public/favicon.svg` were AI-generated at their request | No third-party source was identified; the generating service and its applicable terms were not recorded, so retain this provenance note with the release review |

The inventory was generated from clean Windows desktop dependency installs and the frontend npm lockfile. The optional development dependency note above records packages excluded from the desktop runtime inventory. Regenerate the inventory after dependency changes using the instructions in `THIRD_PARTY_LICENSES.md`. A top-level MIT license does not relicense third-party material.

## Excluded local checkouts

The ignored `mini-coding-agent/`, `pi-agent/`, and `mcp-sever/` directories are local reference or legacy checkouts and are not included in the Git source tree or package contents. The reproducible MCP example lives in `examples/mcp-server/`.

## Release status

**License review is substantially inventoried, but a maintainer review remains required before distribution.** The logo provenance is maintainer-confirmed as AI-generated; the generating service terms remain unknown. This document is a technical inventory note, not legal advice.

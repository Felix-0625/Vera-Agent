# VeraAgent website

The static site keeps three experiences on separate routes:

- `index.html`: product introduction, a desktop-workspace screenshot, and a lightweight CSS animation.
- `design/index.html`: system design documentation rendered from `content/design/index.md`.
- `docs/index.html`: usage and maintenance documentation rendered from `content/docs/*.md`. The overview is the route index; six guides and references are selected from the left sidebar.

The introduction includes interface illustrations for the task board and evaluation loop. They use example labels, not live execution or measured results.

All pages share `assets/site.css`, `assets/site.js`, and `assets/favicon.svg`. Documentation pages use a locally vendored MIT-licensed copy of Marked to render the checked-in Markdown; no build step or CDN is required. Open the site through a local HTTP server so the pages can fetch those Markdown files. Run `python website/check_site.py` to verify page entry points, document sources, local links, fragment anchors, scripts, styles, and images.

The design page includes five diagrams in Chinese and English: runtime architecture, chat/SSE sequence, template-instance-run lifecycle, local data, and the learning loop. SVG exports and a ten-page editable draw.io source live in [diagrams/](diagrams/README.md). Usage/configuration/API references include the traces, scoped memory, evals, and proposal lifecycle.

## GitHub Pages

Public site: https://felix-0625.github.io/Vera-Agent/.

`.github/workflows/website-pages.yml` deploys the `website/` directory from `main` when manually triggered. It first validates local routes and assets. GitHub Pages must be enabled for the repository and configured to use GitHub Actions. The external Actions are pinned to commit SHAs and maintained by weekly Dependabot updates. Check the deployment workflow and the public home/design/docs routes after publishing; successful local validation alone does not prove a public deployment. The homepage links to the versioned source prerelease, not a hosted Agent service.

For another static host, publish the contents of this directory as the site root. No server-side secrets or environment variables are required.

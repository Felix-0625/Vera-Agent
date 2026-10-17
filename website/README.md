# VeraAgent website

The dependency-free static site keeps three experiences on separate routes:

- `index.html`: product/design landing page. It shows a scripted workstation illustration and a lightweight CSS animation; it does not claim to be a recording of live Agent execution.
- `docs/index.html`: documentation with a left-side section index.
- `playground/index.html`: interactive mock built from local JavaScript fixtures. It does not call the desktop app, a model provider, or the visitor's files.

All pages share `assets/site.css`, `assets/site.js`, and `assets/favicon.svg`. Run `python website/check_site.py` to verify the three page entry points, local links, fragment anchors, scripts, styles, and images. The root page remains free of build dependencies.

## GitHub Pages

`.github/workflows/website-pages.yml` deploys the `website/` directory when manually triggered. It first validates local routes and assets. GitHub Pages must already be enabled for the repository and configured to use GitHub Actions. The workflow has not been triggered from this workspace; a successful local validation does not prove a public deployment.

For another static host, publish the contents of this directory as the site root. No server-side secrets or environment variables are required.

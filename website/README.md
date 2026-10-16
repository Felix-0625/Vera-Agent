# VeraAgent introduction page

This is a dependency-free static site. The old landing page and its dedicated styles and scripts have been removed. There is currently no `index.html` at the site root. The documentation (`docs/index.html`) and interactive mock playground (`playground/index.html`) remain available as separate routes. The playground is local JavaScript only. It does not call the desktop application or a model provider, and it never reads the visitor's files.

## Deploy to GitHub Pages

The repository workflow `.github/workflows/website-pages.yml` is manual (`workflow_dispatch`). The site root has no homepage until the landing page is recreated, so do not trigger public deployment yet.

For another static host, upload this directory as the site root. No environment variables or build step are required.

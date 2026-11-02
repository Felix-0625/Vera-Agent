# Deployment

## Desktop application

VeraAgent is distributed as source on GitHub; there is no npm, PyPI, or installer release. The supported shape is a local Windows desktop process: pywebview hosts the built Vite assets and a local Uvicorn API listens on loopback. See [Windows source installation](INSTALL_WINDOWS.md). Do not expose port 8000 on a public interface without a designed authentication boundary.

## Product introduction page

`website/` contains three separate static pages: the product introduction, system design, and documentation. The introduction uses static interface illustrations and does not call the local backend or a model provider. A GitHub Pages workflow is configured as a manual action under `.github/workflows/website-pages.yml`; it validates the local site before deployment and does not publish on every push. The workflow pins external Actions to verified commit SHAs, with weekly Dependabot updates. GitHub Pages must be enabled for the repository with its source set to GitHub Actions, and a maintainer must trigger the workflow. No hosted run or public deployment has been verified from this checkout.

The repository also checks the site in CI and has weekly Dependabot update jobs for GitHub Actions, frontend npm dependencies, and the `uv` backend lockfile. Dependency update pull requests are reviewed and tested; they are not auto-merged.

For another static host, publish the contents of `website/` as the document root. The page uses relative assets and has no API or secret requirement.

## Production readiness boundary

Before distributing a signed installer, define versioned releases, artifact checksums/signing, supported Python/Node/WebView2 versions, dependency update policy, data migration/backup behavior, and an uninstall path. These are not provided by the current source-based installation path.

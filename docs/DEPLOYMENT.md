# Deployment

## Desktop application

The supported current shape is a local Windows desktop process: pywebview hosts the built Vite assets and a local Uvicorn API listens on loopback. See [Windows installation](INSTALL_WINDOWS.md). This is a source bootstrap, not a production-grade signed Windows installer. Do not expose port 8000 on a public interface without a designed authentication boundary.

## Product introduction page

`website/` contains three separate static pages: the design landing page, documentation, and a mock playground. The playground does not call the local backend or a model provider. A GitHub Pages workflow is configured as a manual action under `.github/workflows/website-pages.yml`; it validates the local site before deployment and does not publish on every push. Public deployment still requires an explicit maintainer action in GitHub.

For another static host, publish the contents of `website/` as the document root. The page uses relative assets and has no API or secret requirement.

## Production readiness boundary

Before distributing a signed installer, define versioned releases, artifact checksums/signing, supported Python/Node/WebView2 versions, dependency update policy, data migration/backup behavior, and an uninstall path. These are not claimed to be complete by the current npx bootstrapper.

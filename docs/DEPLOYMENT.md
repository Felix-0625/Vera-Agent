# Deployment

## Desktop application

VeraAgent is distributed through versioned GitHub source prereleases; there is no npm package, PyPI package or signed installer. The supported shape is a local Windows desktop process: pywebview hosts the built Vite assets and a local Uvicorn API listens on loopback. See [Windows source installation](INSTALL_WINDOWS.md). Do not expose port 8000 on a public interface without a designed authentication boundary.

## Product introduction page

`website/` contains three separate static pages: the product introduction, system design, and documentation. The introduction uses static interface illustrations and does not call the local backend or a model provider. The public address is https://felix-0625.github.io/Vera-Agent/.

The manual workflow `.github/workflows/website-pages.yml` validates the site and deploys `website/` from `main`; it does not publish on every push. GitHub Pages must use the GitHub Actions build source. After a documentation update, run **Deploy introduction page** from Actions, verify the exact deployed commit and visit home/design/docs in both languages. A green source CI run alone does not prove deployment. External Actions are pinned to commit SHAs and maintained by Dependabot.

The repository also checks the site in CI and has weekly Dependabot update jobs for GitHub Actions, frontend npm dependencies, and the `uv` backend lockfile. Dependency update pull requests are reviewed and tested; they are not auto-merged.

For another static host, publish the contents of `website/` as the document root. The page uses relative assets and has no API or secret requirement.

## Source release procedure

1. Update the release/frontend version and equivalent PEP 440 Python version, changelog and pinned installation links.
2. Run `./tests/check-all.ps1`, install in a separate directory and record actual UI/provider checks and limitations.
3. Merge the release PR after the backend/frontend/website checks pass. Tag the exact verified `main` commit.
4. Publish an alpha GitHub Release with a source ZIP, `SHA256SUMS.txt`, installation instructions and verification notes. Exclude credentials, `.agents/`, dependency environments and build caches.
5. Deploy the same commit to Pages and check the public installation/download routes. Record workflow URLs with the release.

Protect `main` with required pull requests, the `backend`, `frontend` and `website` status checks, conversation resolution, and no force pushes or deletions. A solo maintainer can require zero approving reviews while still requiring a PR. Delete merged branches automatically; review active dependency PRs before closing or deleting them.

## Production readiness boundary

Before distributing a signed installer, define versioned releases, artifact checksums/signing, supported Python/Node/WebView2 versions, dependency update policy, data migration/backup behavior, and an uninstall path. These are not provided by the current source-based installation path.

# Windows desktop installation

## Source bootstrap through npx

### Current GitHub source command

After the installer files are present on the public GitHub `main` branch, run:

```powershell
npx --yes github:Felix-0625/Agents
```

### npm Registry command after first release

The intended npm package name is `vera-agent-bootstrap-github`; npm Registry returned 404 for that name during this review, so it is currently unpublished and not reserved. Another user may claim it before the first release. After the first public version is published, the Registry command will be:

```powershell
npx --yes vera-agent-bootstrap-github
```

The first Registry publication has not been performed. An npm maintainer must first publish the package under an account that controls the name, then configure npm Trusted Publishing for the `Felix-0625/Agents` repository, workflow file `.github/workflows/npm-publish.yml`, and GitHub environment `npm-release`. The workflow uses GitHub OIDC (`id-token: write`) and requires no long-lived npm write token. Protect the `npm-release` GitHub environment with a required reviewer. A manual workflow run defaults to package dry-run; set its `publish` input to `true` only for an explicitly approved release. npm Trusted Publishing requires npm CLI 11.5.1 or newer and Node.js 22.14 or newer on the publishing runner; the workflow uses Node 24 and installs a compatible npm CLI.

The initial package creation is a one-time manual step because npm Trusted Publishing is configured against an existing package. Use the npm account's 2FA-protected publishing flow and verify the package name and version before publishing. Do not put an npm token in this repository or in chat. Once the package exists and trusted publishing is configured, use the protected workflow for later versions. See [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/) and [npm provenance](https://docs.npmjs.com/generating-provenance-statements/).

The command above runs the repository package directly from GitHub; it does not install from the npm Registry. The package name `vera-agent` is already used on npm, so this project uses the separate bootstrapper name listed above. The npm Registry command remains unavailable until its first package publication.

The bootstrapper asks before changing files, clones or fast-forward-updates the source in `%LOCALAPPDATA%\VeraAgent\app`, creates a small local uv bootstrap environment, installs Python dependencies from the committed `uv.lock`, runs `npm ci`, and starts `start-desktop.ps1`. It does not install Python or Node.js, write system-wide packages, or publish anything.

## Requirements

- Windows 10/11, Node.js 20+ with npm, Git for Windows, and Python 3.10+.
- Microsoft Edge WebView2 Runtime.
- Network access to GitHub, npm, and Python package indexes for the initial dependency download.
- A compatible model provider credential entered by the user after startup.

First launch downloads a comparatively large Python dependency set and frontend packages. It is not an offline installer or a prebuilt signed `.exe`; it builds from source on the user’s machine. If local package indexes or Git mirrors are required, configure them before running the installer.

## Updating and recovery

Run the same command again. The installer only fast-forward updates the matching VeraAgent checkout and stops when tracked local changes exist; it never runs `reset --hard`. Back up `%LOCALAPPDATA%\VeraAgent\app\vera-agent\.agents` before manual repair or reinstall. Close VeraAgent before updating.

## Known limitations

- The command becomes available from the remote GitHub branch after the changes are pushed. It cannot install unpushed workspace changes.
- There is no version-pinned binary release or signed artifact yet.
- First-run dependency installation and launching are Windows-only and require Node, Python and Git to be preinstalled.

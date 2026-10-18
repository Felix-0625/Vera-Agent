# Windows source installation

VeraAgent is currently run from a local source checkout. The project does not provide an npm package, an `npx` installer, a signed executable, or an automatic updater.

## Requirements

- Windows 10 or 11.
- Git for Windows.
- Node.js 20 or newer with npm.
- Python 3.10 or newer.
- uv 0.11.15.
- Microsoft Edge WebView2 Runtime.
- Network access to GitHub, npm, and Python package indexes during setup.

## Install and start

In PowerShell, run:

```powershell
git clone https://github.com/Felix-0625/Agents.git
cd Agents/frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

The frontend and Python dependencies are installed from their lockfiles. The first install downloads packages and can take several minutes. Enter model credentials in VeraAgent's settings after the application opens; do not put API keys in source files.

The launcher checks whether port `8000` already serves VeraAgent. If another application owns that port, it selects the first available port from `8001` through `8100` and builds the desktop frontend with that API address.

## Updating and local data

Close VeraAgent, back up `.agents` data, and update the checkout with Git only when there are no local tracked changes. Rerun `npm ci` and `uv sync --locked --no-dev --extra desktop` after changing dependency lockfiles. Project and conversation data are local and are not synchronized by this source setup.

## Distribution limits

This workflow is for developers and technically comfortable users. It requires Git, Node.js, Python, uv, and WebView2 to be installed separately. It does not provide a version-pinned binary, code signing, automatic updates, or an uninstall program. A signed Windows installer would need a separate release design and verification effort.

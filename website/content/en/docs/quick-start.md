# Quick start

VeraAgent currently starts from GitHub source on Windows 10/11. Installing dependencies requires access to GitHub, npm, and Python package indexes. A model connection also depends on your own provider configuration.

## Requirements

| Dependency | Requirement |
| --- | --- |
| Windows | 10 or 11 |
| Git for Windows | Git and Git Bash for local command tools |
| Node.js | 20 or later, with npm |
| Python | 3.10 or later |
| uv | 0.11 or later |
| Microsoft Edge WebView2 Runtime | Desktop window |

## Install and start

Run in PowerShell:

```powershell
git clone https://github.com/Felix-0625/Agents.git
cd Agents\frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

The script builds the frontend, starts the local API, and opens the desktop window. If port 8000 is occupied, it chooses an available port between 8001 and 8100. You can also double-click `start.bat` from the repository root.

## First use

1. Open **Settings → Models**, add a provider, and enter credentials in the app. The desktop app does not require a manually written `.env` file.
2. Bind a local software-project directory. This records the path; it does not copy the project.
3. Start a conversation under the project. Try a read-only task first, then review permission prompts before modifying files or running commands.
4. For roles and workflows, read [Daily use](usage.md) or the repository [workflow example](../../../../examples/workflow-quickstart/README.md).

## Restart and update

After installation, run `./start-desktop.ps1` from the repository root. Before updating, close the app and back up both the application and project `.agents/` directories. If lockfiles change, run `npm ci` and `uv sync --locked --no-dev --extra desktop` again. There is no auto-updater.

If startup fails, see [Troubleshooting](troubleshooting.md) and the repository [Windows installation guide](../../../../docs/INSTALL_WINDOWS.md).

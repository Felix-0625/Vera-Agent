# Windows source installation

VeraAgent is distributed as source on GitHub and run from a local checkout. There is no npm package, PyPI package, signed executable, or automatic updater. npm is used only to build the frontend.

## Requirements

- Windows 10 or 11.
- Git for Windows.
- Node.js 24 LTS with npm (also supported: 20.19+ or 22.12+).
- Python 3.10 or newer.
- [uv](https://docs.astral.sh/uv/) 0.11 or newer (CI uses 0.11.15).
- Microsoft Edge WebView2 Runtime.
- Network access to GitHub, npm, and Python package indexes during setup.

## Install and start

In PowerShell, run:

```powershell
git clone https://github.com/Felix-0625/Vera-Agent.git
cd Vera-Agent\frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

The frontend and Python dependencies are installed from their lockfiles (`frontend/package-lock.json`, `vera-agent/uv.lock`). The first install downloads packages and can take several minutes. Enter model credentials in VeraAgent's settings (设置 → 模型) after the application opens; do not put API keys in source files.

Next: try [examples/workflow-quickstart](../examples/workflow-quickstart/README.md).

The launcher builds the UI, then `vera_agent.desktop` starts the local API on the first free port from `8000` through `8100`, serves the UI from it, and opens the window.

You can also double-click `start.bat`, which runs the same launcher.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `找不到后端 Python 环境` | Run `uv sync --locked --no-dev --extra desktop` in `vera-agent/` |
| `未安装桌面窗口依赖` | The `desktop` extra is missing; rerun the command above |
| `API server failed to start` | Ports 8000–8100 are all taken, or a dependency failed to import; run `vera-agent\.venv\Scripts\python.exe -m vera_agent.desktop` and read the traceback |
| Terminal tool cannot find bash | Install Git for Windows or set `VERA_AGENT_BASH_PATH` |

## Updating and local data

Close VeraAgent, back up `.agents` data (application data is in `vera-agent/.agents/` of the checkout; see [DATA_MODEL.md](DATA_MODEL.md)), and update the checkout with Git only when there are no local tracked changes. Rerun `npm ci` and `uv sync --locked --no-dev --extra desktop` after changing dependency lockfiles. Project and conversation data are local and are not synchronized by this source setup.

## Distribution limits

This workflow is for developers and technically comfortable users. It requires Git, Node.js, Python, uv, and WebView2 to be installed separately. It does not provide a version-pinned binary, code signing, automatic updates, or an uninstall program. A signed Windows installer would need a separate release design and verification effort.

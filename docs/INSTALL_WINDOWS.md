# Windows desktop installation

## Source bootstrap through npx

After the installer files are present on the public GitHub `main` branch, run:

```powershell
npx --yes github:Felix-0625/Agents
```

This is a GitHub-sourced npm executable; the package name `vera-agent` is already used on npm, so the repository does not claim that name. The current bootstrapper itself is not published to the npm Registry. A Registry installation such as `npx vera-agent` must not be advertised until a package is published under a name the maintainers control.

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

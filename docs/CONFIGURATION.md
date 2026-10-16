# Configuration and local data

VeraAgent currently has more than one configuration location. The Python package uses `platformdirs` for its global `.env` file; the server also stores application/project registries and conversation-related state under `.agents` roots. Exact path selection depends on how the backend is launched and the route being used.

The Windows source installer keeps the checkout under `%LOCALAPPDATA%\VeraAgent\app`; its ignored runtime files remain inside that checkout. Updating source uses fast-forward Git pulls and does not reset user changes. Back up the app’s `.agents` data before manually moving or deleting that directory.

## Credentials

- Configure model credentials in the application or the supported local environment file.
- Never commit `.env`, provider keys, MCP environment values, or session dumps.
- The `.env.example` template documents environment-variable names only; it must not contain usable secrets.
- Treat prompts, tool arguments, logs, and exported conversations as potentially sensitive.

## Project binding

Binding a folder records a local project path. It does not copy or sandbox the project. File-operation scope checks and terminal command permissions are separate controls. The user’s Windows account remains the OS identity used for local commands.

## Backups and updates

Keep a backup before replacing an installation directory. The npx bootstrapper refuses to update a different Git remote or a checkout with tracked local modifications. Ignored `.agents` content is preserved by ordinary fast-forward updates, but it is not automatically backed up or synced.

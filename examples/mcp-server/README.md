# Read-only task board MCP server

This example exposes two read-only tools over MCP stdio: `list_tasks` and `get_task`. Both return a fixed three-task fixture representing a small VeraAgent project. The server does not access the host filesystem, make network requests, or mutate project data.

It uses the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) instead of implementing JSON-RPC or MCP framing by hand.

## Requirements

- Python 3.10 or newer
- `uv` (recommended) or `pip`
- Network access only for the first dependency installation

## Run in the MCP Inspector

From this directory:

```powershell
uv run --with "mcp[cli]>=1.30,<2" mcp dev server.py
```

The Inspector launches the server as a local stdio subprocess. Try `list_tasks` with no arguments, filter by `status`, then call `get_task` with `VA-102`.

## Run the smoke check

```powershell
uv run --with "mcp>=1.30,<2" python test_client.py
```

The client performs a real local MCP handshake, lists the advertised tools, and makes four read-only calls, including a missing-task case. It verifies this example server only; it is not an integration test of VeraAgent's settings UI or a security certification.

Expected output: `MCP stdio smoke check passed: tools/list and 4 read-only calls.` A failed
assertion exits nonzero. The Inspector requires the SDK's `cli` extra; the smoke client does not.
The `<2` bound deliberately keeps this example on the same SDK major as VeraAgent.

## Connect to VeraAgent

In **设置 → MCP**, add a stdio server using the absolute path to
`<checkout>/vera-agent/.venv/Scripts/python.exe` as the command, and the absolute path to
`<checkout>/examples/mcp-server/server.py` as its single argument. Do not enter literal
`<checkout>` placeholders. The server needs no environment variables, headers or API key.

After connecting, require tool discovery to show `list_tasks` and `get_task`. Calling
`list_tasks` returns three fixture tasks; `get_task` with `VA-102` returns one, and an unknown
id returns null. These are embedded fixtures, not your app's current task board.

The sample server writes no files. Stop the Inspector/client to end its subprocess; remove
the MCP entry from settings to disconnect it. Running it again starts with the same fixture.

## Review boundary

The fixture is deliberately read-only and has no permissions beyond its embedded sample data. That does not make third-party MCP servers safe. Before connecting a server to VeraAgent, inspect its source, dependencies, environment variables, filesystem/network access, and the permissions it requests. The MCP host process runs with the operating-system permissions of the user unless a separate sandbox is configured.

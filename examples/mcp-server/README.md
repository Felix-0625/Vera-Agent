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
uv run --with "mcp>=1.12,<2" mcp dev server.py
```

The Inspector launches the server as a local stdio subprocess. Try `list_tasks` with no arguments, filter by `status`, then call `get_task` with `VA-102`.

## Run the smoke check

```powershell
uv run --with "mcp>=1.12,<2" python test_client.py
```

The client performs a real local MCP handshake, lists the advertised tools, and makes four read-only calls, including a missing-task case. It verifies this example server only; it is not an integration test of VeraAgent's settings UI or a security certification.

## Review boundary

The fixture is deliberately read-only and has no permissions beyond its embedded sample data. That does not make third-party MCP servers safe. Before connecting a server to VeraAgent, inspect its source, dependencies, environment variables, filesystem/network access, and the permissions it requests. The MCP host process runs with the operating-system permissions of the user unless a separate sandbox is configured.

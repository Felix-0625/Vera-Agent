# Minimal stdio MCP example

This standalone Python example implements a small JSON-RPC 2.0 stdio server with `system_metrics`, `analyze_codebase`, and `ping_diagnostic` tools. It is intended to illustrate protocol message flow and can be inspected before configuring it in an MCP client.

## Requirements and run

Python 3.10+; no third-party package is required by the server source.

```powershell
cd examples\mcp-server
python server.py
```

The server reads protocol messages from stdin and writes protocol messages to stdout. Diagnostics belong on stderr. For a local client smoke check:

```powershell
python test_client.py
```

The smoke client starts the local server process and sends protocol requests. It does not test VeraAgent's settings UI or certify the security of arbitrary MCP servers. `analyze_codebase` inspects paths provided to it; run it only against a directory you trust.

## Configure manually

An MCP client typically needs the absolute path to a Python interpreter and this example's `server.py` as arguments. Configuration formats vary by client/version; use that client's current documentation rather than copying a stale global config template.

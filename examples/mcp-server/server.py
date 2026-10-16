"""Minimal MCP (Model Context Protocol) stdio JSON-RPC 2.0 server.

Transport contract:
    * Requests arrive one JSON object per line on ``stdin``.
    * Responses are written one JSON object per line to ``stdout`` (flushed).
    * ALL logging goes to ``stderr`` — stdout must stay pure JSON-RPC.

Supported methods:
    * ``initialize``  — handshake; advertises capabilities + server info.
    * ``tools/list``  — enumerate available tools.
    * ``tools/call``  — invoke a tool by name.
    * ``ping`` / ``notifications/initialized`` — trivial liveness helpers.

Usage:
    python server.py [--workspace PATH] [--log-level LEVEL]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict, Optional

import protocol as rpc
import tools

__all__ = ["MCPServer", "main"]

logger = logging.getLogger("mcp.server")

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "mcp-stdio-server"
SERVER_VERSION = "0.1.0"


def _configure_logging(level: str) -> None:
    """Route every log record to stderr, never stdout."""
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


class MCPServer:
    """Line-delimited JSON-RPC 2.0 event loop over stdin/stdout."""

    def __init__(self, stdin: Any = None, stdout: Any = None) -> None:
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._initialized = False

    # -- transport -----------------------------------------------------------
    def _write(self, response: rpc.Response) -> None:
        """Serialise and flush a single response line to stdout."""
        payload = response.to_json()
        self._stdout.write(payload + "\n")
        self._stdout.flush()
        logger.debug("-> %s", payload)

    # -- dispatch ------------------------------------------------------------
    def handle_message(self, line: str) -> Optional[rpc.Response]:
        """Process one raw input line, returning a response (or ``None``)."""
        line = line.strip()
        if not line:
            return None

        logger.debug("<- %s", line)

        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("failed to parse request: %s", exc)
            return rpc.make_error_response(None, rpc.PARSE_ERROR, "Parse error")

        # JSON-RPC batch requests are not supported by this skeleton.
        if isinstance(payload, list):
            logger.warning("batch requests are not supported")
            return rpc.make_error_response(
                None, rpc.INVALID_REQUEST, "Batch requests are not supported"
            )

        try:
            request = rpc.Request.from_dict(payload)
        except ValueError as exc:
            request_id = payload.get("id") if isinstance(payload, dict) else None
            logger.warning("invalid request: %s", exc)
            return rpc.make_error_response(
                request_id, rpc.INVALID_REQUEST, f"Invalid Request: {exc}"
            )

        if request.jsonrpc != rpc.JSONRPC_VERSION:
            if request.is_notification:
                logger.warning("ignoring notification with bad jsonrpc version")
                return None
            return rpc.make_error_response(
                request.id, rpc.INVALID_REQUEST, "Invalid Request: jsonrpc must be '2.0'"
            )

        try:
            result = self._dispatch(request)
        except rpc.MethodNotFound as exc:
            logger.warning("method not found: %s", exc)
            if request.is_notification:
                return None
            return rpc.make_error_response(request.id, rpc.METHOD_NOT_FOUND, str(exc))
        except tools.ToolError as exc:
            # Tool-level failures surface as a successful RPC carrying isError.
            if request.is_notification:
                return None
            return rpc.make_result_response(request.id, tools.error_result(str(exc)))
        except Exception as exc:  # noqa: BLE001 - last-resort guard
            logger.exception("internal error handling %s", request.method)
            if request.is_notification:
                return None
            return rpc.make_error_response(
                request.id, rpc.INTERNAL_ERROR, "Internal error", data=str(exc)
            )

        if request.is_notification:
            logger.debug("notification %s handled (no response)", request.method)
            return None
        return rpc.make_result_response(request.id, result)

    def _dispatch(self, request: rpc.Request) -> Any:
        """Route a validated request to its handler."""
        handler = _HANDLERS.get(request.method)
        if handler is None:
            raise rpc.MethodNotFound(f"Method not found: {request.method}")
        return handler(self, request.params or {})

    # -- handlers ------------------------------------------------------------
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        client_info = params.get("clientInfo") or {}
        logger.info(
            "initialize from client=%s version=%s protocol=%s",
            client_info.get("name", "unknown"),
            client_info.get("version", "unknown"),
            params.get("protocolVersion", "unknown"),
        )
        self._initialized = True
        return {
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    def _handle_tools_list(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {"tools": tools.list_tool_definitions()}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise tools.ToolError("'name' is required and must be a string", "INVALID_ARGUMENT")

        arguments = params.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise tools.ToolError("'arguments' must be an object", "INVALID_ARGUMENT")

        logger.info("tools/call name=%s", name)
        return tools.call_tool(name, arguments)

    def _handle_ping_diagnostic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Protocol-level convenience alias for the ``ping_diagnostic`` tool."""
        arguments = params.get("arguments", params) or {}
        if not isinstance(arguments, dict):
            raise tools.ToolError("'arguments' must be an object", "INVALID_ARGUMENT")
        logger.info("ping_diagnostic invoked")
        return tools.call_tool("ping_diagnostic", arguments)

    def _handle_ping(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def _handle_initialized_notification(self, _params: Dict[str, Any]) -> None:
        logger.info("client signalled notifications/initialized")
        return None

    # -- loop ----------------------------------------------------------------
    def serve_forever(self) -> int:
        """Run the read/dispatch/write loop until EOF or a fatal I/O error."""
        logger.info("%s v%s listening on stdio", SERVER_NAME, SERVER_VERSION)
        try:
            for line in self._stdin:
                try:
                    response = self.handle_message(line)
                except Exception:  # noqa: BLE001 - never let one line kill the loop
                    logger.exception("unhandled error while processing a line")
                    continue
                if response is not None:
                    self._write(response)
        except KeyboardInterrupt:  # pragma: no cover - interactive abort
            logger.info("interrupted, shutting down")
            return 130
        logger.info("stdin closed, shutting down")
        return 0


_HANDLERS = {
    "initialize": MCPServer._handle_initialize,
    "tools/list": MCPServer._handle_tools_list,
    "tools/call": MCPServer._handle_tools_call,
    "ping_diagnostic": MCPServer._handle_ping_diagnostic,
    "ping": MCPServer._handle_ping,
    "notifications/initialized": MCPServer._handle_initialized_notification,
}


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP stdio JSON-RPC 2.0 server")
    parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace root used by tools (defaults to the current directory).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="stderr log verbosity.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.log_level)

    if args.workspace:
        from pathlib import Path

        workspace = Path(args.workspace).expanduser().resolve(strict=False)
        if not workspace.is_dir():
            logger.error("workspace is not a directory: %s", workspace)
            return 2
        tools.WORKSPACE_ROOT = workspace
        logger.info("workspace root set to %s", workspace)

    server = MCPServer()
    return server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())

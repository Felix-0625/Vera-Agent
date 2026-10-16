"""Standalone verification client for the MCP stdio JSON-RPC 2.0 server.

Spawns ``python server.py`` as a subprocess, drives it over stdin/stdout using
the Model Context Protocol handshake, exercises every advertised tool and then
shuts the server down cleanly.

Run with:
    python test_client.py

Exit code 0 means every check passed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional

SERVER_CMD = [sys.executable, "server.py", "--log-level", "INFO"]
PROTOCOL_VERSION = "2024-11-05"
EXPECTED_TOOLS = ["system_metrics", "analyze_codebase", "ping_diagnostic"]
REQUEST_TIMEOUT = 30.0


class CheckFailure(AssertionError):
    """Raised when a verification assertion fails."""


def check(condition: bool, message: str) -> None:
    """Assert ``condition`` with a clear, prefixed failure message."""
    if not condition:
        raise CheckFailure(message)
    print(f"  [ok] {message}")


class MCPClient:
    """Minimal JSON-RPC 2.0 client speaking the MCP stdio transport."""

    def __init__(self, cmd: Optional[List[str]] = None) -> None:
        self._cmd = cmd or SERVER_CMD
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 0
        self._stderr_lines: List[str] = []
        self._stderr_thread: Optional[threading.Thread] = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        """Launch the server subprocess with piped stdio."""
        print(f"$ {' '.join(self._cmd)}")
        self._proc = subprocess.Popen(
            self._cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)) or ".",
        )

        # Drain stderr on a daemon thread so the server never blocks on a full
        # pipe buffer while we are waiting for a stdout response.
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        for line in self._proc.stderr:
            self._stderr_lines.append(line.rstrip("\n"))

    def close(self) -> int:
        """Close stdin, reap the process and return its exit code."""
        assert self._proc is not None
        if self._proc.stdin and not self._proc.stdin.closed:
            self._proc.stdin.close()
        try:
            code = self._proc.wait(timeout=REQUEST_TIMEOUT)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            code = self._proc.wait(timeout=REQUEST_TIMEOUT)
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=REQUEST_TIMEOUT)
        return code

    # -- transport -----------------------------------------------------------
    def _send(self, payload: Dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        line = json.dumps(payload, separators=(",", ":"))
        try:
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise CheckFailure(f"failed to write request to server: {exc}") from exc

    def _read_response(self) -> Dict[str, Any]:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = self._proc.stdout.readline()
            if line == "":
                stderr_tail = "\n".join(self._stderr_lines[-20:])
                raise CheckFailure(
                    "server closed stdout unexpectedly (no response).\n"
                    f"last stderr:\n{stderr_tail}"
                )
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError as exc:
                raise CheckFailure(f"non-JSON payload on stdout: {line!r} ({exc})") from exc

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a request and assert its response is a valid JSON-RPC reply."""
        self._next_id += 1
        request_id = self._next_id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

        response = self._read_response()
        check(response.get("jsonrpc") == "2.0", f"{method}: response jsonrpc == '2.0'")
        check(response.get("id") == request_id, f"{method}: response id == {request_id}")
        check(
            ("result" in response) != ("error" in response),
            f"{method}: response carries exactly one of result/error",
        )
        return response

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    # -- introspection -------------------------------------------------------
    @property
    def stderr_text(self) -> str:
        return "\n".join(self._stderr_lines)


def extract_text(result: Dict[str, Any]) -> str:
    """Pull the concatenated text out of an MCP tool result payload."""
    content = result.get("content")
    check(isinstance(content, list) and content, "tool result contains a non-empty content list")
    first = content[0]
    check(first.get("type") == "text", "tool result content[0].type == 'text'")
    check(
        result.get("isError") is False,
        "tool result isError == False",
    )
    return first.get("text", "")


# ---------------------------------------------------------------------------
# Test phases
# ---------------------------------------------------------------------------
def test_initialize(client: MCPClient) -> None:
    print("\n[1/5] initialize handshake")
    response = client.request(
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test_client", "version": "1.0.0"},
        },
    )
    check("error" not in response, "initialize returned a result (no error)")
    result = response["result"]

    check("protocolVersion" in result, f"handshake advertises protocolVersion={result.get('protocolVersion')!r}")
    check(isinstance(result.get("capabilities"), dict), "handshake advertises a capabilities object")
    check(
        "tools" in result["capabilities"],
        "capabilities.tools is present",
    )

    server_info = result.get("serverInfo")
    check(isinstance(server_info, dict), "handshake advertises serverInfo")
    check(bool(server_info.get("name")), f"serverInfo.name = {server_info.get('name')!r}")
    check(bool(server_info.get("version")), f"serverInfo.version = {server_info.get('version')!r}")

    # Protocol requires the client to acknowledge the handshake.
    client.notify("notifications/initialized")
    print("  [ok] sent notifications/initialized")


def test_tools_list(client: MCPClient) -> None:
    print("\n[2/5] tools/list")
    response = client.request("tools/list", {})
    check("error" not in response, "tools/list returned a result (no error)")

    tool_defs = response["result"].get("tools")
    check(isinstance(tool_defs, list), "result.tools is a list")
    check(len(tool_defs) == 3, f"exactly 3 tool definitions advertised (got {len(tool_defs)})")

    names = [tool.get("name") for tool in tool_defs]
    check(set(names) == set(EXPECTED_TOOLS), f"tool names == {EXPECTED_TOOLS}")

    for tool in tool_defs:
        name = tool.get("name")
        check(isinstance(tool.get("description"), str) and tool["description"], f"{name}: has a description")
        schema = tool.get("inputSchema")
        check(isinstance(schema, dict) and schema.get("type") == "object", f"{name}: inputSchema is an object schema")

    print(f"  [ok] advertised tools: {names}")


def test_system_metrics(client: MCPClient) -> None:
    print("\n[3/5] tools/call -> system_metrics")
    response = client.request("tools/call", {"name": "system_metrics", "arguments": {}})
    check("error" not in response, "system_metrics returned a result (no error)")
    text = extract_text(response["result"])

    for needle in ("platform", "python_version", "workspace_root"):
        check(needle in text, f"report contains '{needle}'")
    check("Linux" in text or "Windows" in text or "Darwin" in text, "report identifies the host OS")
    print("  --- system_metrics output ---")
    for line in text.splitlines():
        print(f"      {line}")


def test_analyze_codebase(client: MCPClient) -> None:
    print("\n[4/5] tools/call -> analyze_codebase")
    response = client.request(
        "tools/call", {"name": "analyze_codebase", "arguments": {"path": "."}}
    )
    check("error" not in response, "analyze_codebase returned a result (no error)")
    text = extract_text(response["result"])

    for needle in ("total_files", "code_files", "code_lines"):
        check(needle in text, f"report contains '{needle}'")

    metrics: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metrics[key.strip()] = value.strip()

    total_files = int(metrics.get("total_files", "-1"))
    code_files = int(metrics.get("code_files", "-1"))
    code_lines = int(metrics.get("code_lines", "-1"))

    check(total_files >= 4, f"total_files >= 4 (found {total_files})")
    check(code_files >= 3, f"code_files >= 3 (found {code_files})")
    check(code_lines > 0, f"code_lines > 0 (found {code_lines})")
    check(code_files <= total_files, "code_files does not exceed total_files")
    print("  --- analyze_codebase output ---")
    for line in text.splitlines():
        print(f"      {line}")


def test_ping_diagnostic(client: MCPClient) -> None:
    print("\n[5/5] tools/call -> ping_diagnostic")
    probe = "client-health-probe"
    response = client.request(
        "tools/call", {"name": "ping_diagnostic", "arguments": {"message": probe}}
    )
    check("error" not in response, "ping_diagnostic returned a result (no error)")
    text = extract_text(response["result"])

    check(text.startswith("Diagnostic: healthy"), "report header says 'Diagnostic: healthy'")

    _, _, json_body = text.partition("\n")
    report = json.loads(json_body)
    check(report.get("status") == "healthy", f"report status == 'healthy' (got {report.get('status')!r})")
    check(report.get("message") == probe, f"report echoes message == {probe!r}")

    timestamp = report.get("timestamp", "")
    check(bool(timestamp) and "T" in timestamp, f"report carries an ISO-8601 timestamp ({timestamp!r})")
    # Round-trip the timestamp to prove it is genuinely ISO-8601 parseable.
    from datetime import datetime

    parsed = datetime.fromisoformat(timestamp)
    check(parsed.tzinfo is not None, f"timestamp is timezone-aware ({parsed.tzinfo})")
    print("  --- ping_diagnostic output ---")
    for line in text.splitlines():
        print(f"      {line}")


def main() -> int:
    print("=" * 68)
    print(" MCP stdio server verification client")
    print("=" * 68)

    client = MCPClient()
    exit_code = 0
    try:
        client.start()
        test_initialize(client)
        test_tools_list(client)
        test_system_metrics(client)
        test_analyze_codebase(client)
        test_ping_diagnostic(client)
    except CheckFailure as exc:
        print(f"\n[TEST FAILED] {exc}", file=sys.stderr)
        exit_code = 1
    except Exception as exc:  # noqa: BLE001 - surface any transport surprise
        print(f"\n[TEST ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        if client._proc is not None:
            print("\n[shutdown] closing stdin and waiting for the server to exit")
            code = client.close()
            if code != 0:
                print(f"[TEST FAILED] server exited with non-zero code {code}", file=sys.stderr)
                exit_code = 1
            else:
                print("  [ok] server exited cleanly with code 0")

            stderr_text = client.stderr_text
            if stderr_text:
                print("  --- captured server stderr (logs must never touch stdout) ---")
                for line in stderr_text.splitlines()[:10]:
                    print(f"      {line}")

    if exit_code == 0:
        print("\n[TEST PASSED] All MCP tools verified successfully!")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

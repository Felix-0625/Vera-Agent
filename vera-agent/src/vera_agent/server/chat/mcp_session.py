"""Connect the MCP servers attached to a chat turn and expose their tools to the model.

Each enabled server (stdio command or HTTP(S) remote) is opened inside the caller's
`AsyncExitStack`, so connections close when the stream ends. Tools are exposed as
`mcp__<server>__<tool>`; a server that fails to start yields a `thinking` notice instead.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.chat")


async def connect_attached_mcps(
    stack: AsyncExitStack,
    state: ServerState,
    attached_mcps: list[str],
    target_cwd: Path,
    mcp_tools: list[dict],
    mcp_dispatch: dict[str, tuple[Any, str]],
) -> AsyncIterator[str]:
    """Fill ``mcp_tools`` (model schemas) and ``mcp_dispatch`` (name -> session, remote tool)."""
    if isinstance(attached_mcps, list) and attached_mcps:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.streamable_http import streamablehttp_client

        configured = state.load_json_config("mcp_servers.json", {"servers": []}).get("servers", [])
        by_id = {str(item.get("id")): item for item in configured if isinstance(item, dict)}
        for server_id in dict.fromkeys(str(value) for value in attached_mcps):
            server = by_id.get(server_id)
            if not server or not server.get("enabled"):
                continue
            try:
                if server.get("type") == "remote":
                    remote_url = str(server.get("url") or "")
                    if not remote_url.startswith(("https://", "http://")):
                        raise ValueError("Remote MCP URL must use HTTP or HTTPS.")
                    read_stream, write_stream, _ = await stack.enter_async_context(
                        streamablehttp_client(remote_url, headers=server.get("headers") or {})
                    )
                else:
                    command = str(server.get("command") or "")
                    args = server.get("args") or []
                    if not command or not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
                        continue
                    if os.name == "nt":
                        resolved_command = shutil.which(command)
                        if resolved_command and resolved_command.lower().endswith((".cmd", ".bat")):
                            command_line = subprocess.list2cmdline([resolved_command, *args])
                            command = os.environ.get("COMSPEC", "cmd.exe")
                            args = ["/d", "/s", "/c", command_line]
                    inherited_keys = (
                        "PATH",
                        "Path",
                        "SYSTEMROOT",
                        "SystemRoot",
                        "WINDIR",
                        "TEMP",
                        "TMP",
                        "HOME",
                        "USERPROFILE",
                        "APPDATA",
                        "LOCALAPPDATA",
                    )
                    launch_env = {key: os.environ[key] for key in inherited_keys if key in os.environ}
                    configured_env = server.get("env") or {}
                    if not isinstance(configured_env, dict) or not all(
                        isinstance(key, str) and isinstance(value, str) for key, value in configured_env.items()
                    ):
                        raise ValueError("MCP environment variables must be string key-value pairs.")
                    parameters = StdioServerParameters(
                        command=command, args=args, env={**launch_env, **configured_env}, cwd=str(target_cwd)
                    )
                    read_stream, write_stream = await stack.enter_async_context(stdio_client(parameters))
                client = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await client.initialize()
                tool_result = await client.list_tools()
                for remote_tool in tool_result.tools:
                    safe_server = re.sub(r"[^a-zA-Z0-9_-]", "_", server_id)
                    safe_tool = re.sub(r"[^a-zA-Z0-9_-]", "_", remote_tool.name)
                    exposed_name = f"mcp__{safe_server}__{safe_tool}"
                    if exposed_name in mcp_dispatch:
                        continue
                    schema = remote_tool.inputSchema or {"type": "object", "properties": {}}
                    mcp_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": exposed_name,
                                "description": remote_tool.description or f"MCP tool {remote_tool.name}",
                                "parameters": schema,
                            },
                        }
                    )
                    mcp_dispatch[exposed_name] = (client, remote_tool.name)
            except Exception as error:
                logger.warning("MCP server %s failed to initialize: %s", server_id, error)
                server_label = str(server.get("name") or server_id)
                notice = {"step": 0, "content": f"MCP {server_label} 连接失败：{error}"}
                yield f"event: thinking\ndata: {json.dumps(notice, ensure_ascii=False)}\n\n"

"""Exercise the sample MCP server through its real stdio client transport."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER = Path(__file__).with_name("server.py")


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=str(SERVER.parent),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            assert tool_names == {"list_tasks", "get_task"}, tool_names

            listed = await session.call_tool("list_tasks", {})
            assert not listed.isError
            assert len(listed.structuredContent["result"]) == 3

            filtered = await session.call_tool("list_tasks", {"status": "in_progress"})
            assert not filtered.isError
            assert [task["id"] for task in filtered.structuredContent["result"]] == ["VA-101"]

            found = await session.call_tool("get_task", {"task_id": "VA-102"})
            assert not found.isError
            assert found.structuredContent["result"]["title"] == "审查工作流信息传递"

            missing = await session.call_tool("get_task", {"task_id": "missing"})
            assert not missing.isError
            assert missing.structuredContent["result"] is None

            print("MCP stdio smoke check passed: tools/list and 4 read-only calls.")


if __name__ == "__main__":
    asyncio.run(main())

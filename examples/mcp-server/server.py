"""A tiny read-only MCP server backed by fixed sample tasks."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("VeraAgent sample task board")

_TASKS = (
    {
        "id": "VA-101",
        "title": "检查任务状态同步",
        "status": "in_progress",
        "owner": "主 Agent",
    },
    {
        "id": "VA-102",
        "title": "审查工作流信息传递",
        "status": "todo",
        "owner": "流程 Agent",
    },
    {
        "id": "VA-103",
        "title": "复核代码审查清单",
        "status": "done",
        "owner": "审查 Agent",
    },
)


@mcp.tool()
def list_tasks(
    status: Literal["todo", "in_progress", "done"] | None = None,
) -> list[dict[str, str]]:
    """List the sample project's fixed tasks, optionally filtered by status."""
    if status is None:
        return list(_TASKS)
    return [task for task in _TASKS if task["status"] == status]


@mcp.tool()
def get_task(task_id: str) -> dict[str, str] | None:
    """Return one sample task by its ID, or null when it is not in the fixture."""
    return next((task for task in _TASKS if task["id"] == task_id), None)


if __name__ == "__main__":
    mcp.run(transport="stdio")

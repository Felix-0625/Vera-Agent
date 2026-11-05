"""Turn one parsed tool call into an action dict, shared by the chat-completions and Responses API parsers.

The two APIs differ only in where a call keeps its name, arguments and id; what makes the arguments valid is
the same, so it lives here once.
"""

from __future__ import annotations

from typing import Any

DELEGATION_TOOLS = ("delegate_research", "delegate_review")
_PREVIEW_CHARS = 50


def build_action(tool_name: str, args: dict[str, Any], call_id: str | None) -> tuple[dict | None, str]:
    """``(action, "")`` for valid arguments, or ``(None, problem)`` describing what is missing.

    ``tool_name`` must already be a known built-in tool and ``args`` a JSON object.
    """
    if tool_name == "bash":
        if "command" not in args:
            return None, "Missing 'command' argument in bash tool call."
        action: dict[str, Any] = {"command": args["command"], "tool_call_id": call_id}
        if args.get("timeout") is not None:
            action["timeout"] = args["timeout"]
        return action, ""
    if tool_name == "read":
        if "path" not in args:
            return None, "Missing 'path' argument in read tool call."
        return {
            "tool_name": "read",
            "path": args["path"],
            "offset": args.get("offset", 1),
            "limit": args.get("limit", 2000),
            "command": f"read {args['path']}",
            "tool_call_id": call_id,
        }, ""
    if tool_name == "write":
        if "path" not in args or "content" not in args:
            return None, "Missing 'path' or 'content' argument in write tool call."
        return {
            "tool_name": "write",
            "path": args["path"],
            "content": args["content"],
            "command": f"write {args['path']}",
            "tool_call_id": call_id,
        }, ""
    if tool_name == "edit":
        edits = args.get("edits")
        if not edits and "oldText" in args and "newText" in args:
            edits = [{"oldText": args["oldText"], "newText": args["newText"]}]  # single-edit shorthand
        if "path" not in args or not edits:
            return None, "Missing 'path' or 'edits' argument in edit tool call."
        return {
            "tool_name": "edit",
            "path": args["path"],
            "edits": edits,
            "command": f"edit {args['path']}",
            "tool_call_id": call_id,
        }, ""
    if tool_name in DELEGATION_TOOLS:
        task_text = args.get("task") or args.get("command") or ""
        if not task_text:
            return None, f"Missing 'task' argument in {tool_name} tool call."
        preview = (task_text[:_PREVIEW_CHARS] + "...") if len(task_text) > _PREVIEW_CHARS else task_text
        return {
            "tool_name": tool_name,
            "task": task_text,
            "command": f"{tool_name} {preview}",
            "tool_call_id": call_id,
        }, ""
    return None, ""

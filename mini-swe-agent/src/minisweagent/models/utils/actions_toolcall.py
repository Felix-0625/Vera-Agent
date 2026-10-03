"""Parse actions & format observations with toolcalls"""

import json
import time

from jinja2 import StrictUndefined, Template

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.openai_multimodal import expand_multimodal_content

from minisweagent.tools import (
    ALL_TOOLS,
    BASH_TOOL,
    EDIT_TOOL,
    READ_TOOL,
    TOOL_NAMES,
    WRITE_TOOL,
)


def parse_toolcall_actions(
    tool_calls: list | None,
    *,
    format_error_template: str,
    template_kwargs: dict | None = None,
    allow_empty: bool = False,
) -> list[dict]:
    """Parse tool calls from the response. Supports read, write, edit, and bash tools."""
    template_kwargs = template_kwargs or {}
    if not tool_calls:
        if allow_empty:
            return []
        error_text = Template(format_error_template, undefined=StrictUndefined).render(
            error="No tool calls found in the response. Every response MUST include at least one tool call.",
            actions=[],
            has_tool_calls=False,
            **template_kwargs,
        )
        raise FormatError(
            {
                "role": "user",
                "content": error_text,
                "extra": {"interrupt_type": "FormatError"},
            }
        )
    actions = []
    for tool_call in tool_calls:
        error_msg = ""
        args = {}
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception as e:
            error_msg = f"Error parsing tool call arguments: {e}."

        tool_name = tool_call.function.name
        if tool_name not in TOOL_NAMES:
            error_msg += f"Unknown tool '{tool_name}'. Available tools: {', '.join(sorted(TOOL_NAMES))}."
        elif not isinstance(args, dict):
            error_msg += f"Tool arguments for '{tool_name}' must be a JSON dictionary."
        else:
            if tool_name == "bash":
                if "command" not in args:
                    error_msg += "Missing 'command' argument in bash tool call."
                else:
                    action = {"command": args["command"], "tool_call_id": tool_call.id}
                    if "timeout" in args and args["timeout"] is not None:
                        action["timeout"] = args["timeout"]
                    actions.append(action)
            elif tool_name == "read":
                if "path" not in args:
                    error_msg += "Missing 'path' argument in read tool call."
                else:
                    actions.append(
                        {
                            "tool_name": "read",
                            "path": args["path"],
                            "offset": args.get("offset", 1),
                            "limit": args.get("limit", 2000),
                            "command": f"read {args['path']}",
                            "tool_call_id": tool_call.id,
                        }
                    )
            elif tool_name == "write":
                if "path" not in args or "content" not in args:
                    error_msg += "Missing 'path' or 'content' argument in write tool call."
                else:
                    actions.append(
                        {
                            "tool_name": "write",
                            "path": args["path"],
                            "content": args["content"],
                            "command": f"write {args['path']}",
                            "tool_call_id": tool_call.id,
                        }
                    )
            elif tool_name == "edit":
                edits = args.get("edits")
                if not edits and "oldText" in args and "newText" in args:
                    edits = [{"oldText": args["oldText"], "newText": args["newText"]}]
                if "path" not in args or not edits:
                    error_msg += "Missing 'path' or 'edits' argument in edit tool call."
                else:
                    actions.append(
                        {
                            "tool_name": "edit",
                            "path": args["path"],
                            "edits": edits,
                            "command": f"edit {args['path']}",
                            "tool_call_id": tool_call.id,
                        }
                    )

        if error_msg:
            raise FormatError(
                {
                    "role": "user",
                    "content": Template(format_error_template, undefined=StrictUndefined).render(
                        actions=[], error=error_msg.strip(), has_tool_calls=True, **template_kwargs
                    ),
                    "extra": {"interrupt_type": "FormatError"},
                }
            )
    return actions


def format_toolcall_observation_messages(
    *,
    actions: list[dict],
    outputs: list[dict],
    observation_template: str,
    template_vars: dict | None = None,
    multimodal_regex: str = "",
) -> list[dict]:
    """Format execution outputs into tool result messages."""
    not_executed = {"output": "", "returncode": -1, "exception_info": "action was not executed"}
    padded_outputs = outputs + [not_executed] * (len(actions) - len(outputs))
    results = []
    for action, output in zip(actions, padded_outputs):
        content = Template(observation_template, undefined=StrictUndefined).render(
            output=output, **(template_vars or {})
        )
        msg = {
            "content": content,
            "extra": {
                "raw_output": output.get("output", ""),
                "returncode": output.get("returncode"),
                "timestamp": time.time(),
                "exception_info": output.get("exception_info"),
                **output.get("extra", {}),
            },
        }
        if "tool_call_id" in action:
            msg["tool_call_id"] = action["tool_call_id"]
            msg["role"] = "tool"
        else:
            msg["role"] = "user"  # human issued commands
        if multimodal_regex:
            msg = expand_multimodal_content(msg, pattern=multimodal_regex)
        results.append(msg)
    return results

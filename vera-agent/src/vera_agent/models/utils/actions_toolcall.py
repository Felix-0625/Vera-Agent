"""Parse actions & format observations with toolcalls"""

import json
import time

from jinja2 import StrictUndefined, Template

from vera_agent.exceptions import FormatError
from vera_agent.models.utils.openai_multimodal import expand_multimodal_content
from vera_agent.models.utils.tool_arguments import build_action
from vera_agent.tools import (
    ALL_TOOLS,
    BASH_TOOL,
    EDIT_TOOL,
    READ_TOOL,
    TOOL_NAMES,
    WRITE_TOOL,
)

# Tool schemas are re-exported so model adapters can import them next to the parser.
__all__ = [
    "ALL_TOOLS",
    "BASH_TOOL",
    "EDIT_TOOL",
    "READ_TOOL",
    "WRITE_TOOL",
    "format_toolcall_observation_messages",
    "parse_toolcall_actions",
]


def _format_error(template: str, template_kwargs: dict, *, error: str, has_tool_calls: bool) -> FormatError:
    content = Template(template, undefined=StrictUndefined).render(
        error=error, actions=[], has_tool_calls=has_tool_calls, **template_kwargs
    )
    return FormatError({"role": "user", "content": content, "extra": {"interrupt_type": "FormatError"}})


def parse_toolcall_actions(
    tool_calls: list | None,
    *,
    format_error_template: str,
    template_kwargs: dict | None = None,
    allow_empty: bool = False,
    additional_tool_names: set[str] | None = None,
) -> list[dict]:
    """Parse tool calls from the response. Supports read, write, edit, bash, delegation and extra (MCP) tools."""
    template_kwargs = template_kwargs or {}
    extra_tools = additional_tool_names or set()
    if not tool_calls:
        if allow_empty:
            return []
        message = "No tool calls found in the response. Every response MUST include at least one tool call."
        raise _format_error(format_error_template, template_kwargs, error=message, has_tool_calls=False)
    actions = []
    for tool_call in tool_calls:
        error_msg = ""
        args = {}
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception as e:
            error_msg = f"Error parsing tool call arguments: {e}."

        tool_name = tool_call.function.name
        if tool_name not in TOOL_NAMES and tool_name not in extra_tools:
            error_msg += f"Unknown tool '{tool_name}'. Available tools: {', '.join(sorted(TOOL_NAMES))}."
        elif not isinstance(args, dict):
            error_msg += f"Tool arguments for '{tool_name}' must be a JSON dictionary."
        elif tool_name in extra_tools:
            actions.append(
                {"tool_name": tool_name, "arguments": args, "command": f"MCP {tool_name}", "tool_call_id": tool_call.id}
            )
        else:
            action, problem = build_action(tool_name, args, tool_call.id)
            error_msg += problem
            if action:
                actions.append(action)
        if error_msg:
            raise _format_error(format_error_template, template_kwargs, error=error_msg.strip(), has_tool_calls=True)
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

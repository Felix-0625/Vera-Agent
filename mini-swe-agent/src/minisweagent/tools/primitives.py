"""Pi-agent style 4 orthogonal primitive tool definitions (read, write, edit, bash)."""

READ_TOOL = {
    "type": "function",
    "function": {
        "name": "read",
        "description": (
            "Read file contents. Supports line numbers, offset, and limit for large files. "
            "Always inspect code with read before making edits."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative or absolute)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed, default: 1)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 2000)",
                },
            },
            "required": ["path"],
        },
    },
}

WRITE_TOOL = {
    "type": "function",
    "function": {
        "name": "write",
        "description": (
            "Create a new file or completely overwrite an existing file with new content. "
            "Automatically creates parent directories. Use write only for new files or complete rewrites; "
            "for targeted modifications to existing files, use edit instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative or absolute)",
                },
                "content": {
                    "type": "string",
                    "description": "Full content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
}

EDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "edit",
        "description": (
            "Make precise surgical edits to a file by exact text replacement. "
            "Each edit specifies exact oldText (which must match uniquely in the file) "
            "and newText. Multiple disjoint edits can be applied in one call."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit (relative or absolute)",
                },
                "edits": {
                    "type": "array",
                    "description": "List of targeted replacements. Each oldText must be unique in the file.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "Exact text to be replaced (must match uniquely in the file)",
                            },
                            "newText": {
                                "type": "string",
                                "description": "Replacement text for this targeted edit",
                            },
                        },
                        "required": ["oldText", "newText"],
                    },
                },
            },
            "required": ["path", "edits"],
        },
    },
}

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a shell command (e.g., git, pytest, build, grep, find).",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["command"],
        },
    },
}

ALL_TOOLS = [READ_TOOL, WRITE_TOOL, EDIT_TOOL, BASH_TOOL]
TOOL_NAMES = {"read", "write", "edit", "bash"}

# OpenAI Responses API flat schema definitions (without nested function dictionary)
READ_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "read",
    "description": READ_TOOL["function"]["description"],
    "parameters": READ_TOOL["function"]["parameters"],
}

WRITE_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "write",
    "description": WRITE_TOOL["function"]["description"],
    "parameters": WRITE_TOOL["function"]["parameters"],
}

EDIT_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "edit",
    "description": EDIT_TOOL["function"]["description"],
    "parameters": EDIT_TOOL["function"]["parameters"],
}

BASH_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "bash",
    "description": BASH_TOOL["function"]["description"],
    "parameters": BASH_TOOL["function"]["parameters"],
}

ALL_TOOLS_RESPONSE_API = [
    READ_TOOL_RESPONSE_API,
    WRITE_TOOL_RESPONSE_API,
    EDIT_TOOL_RESPONSE_API,
    BASH_TOOL_RESPONSE_API,
]

from minisweagent.tools.subagent_tools import (
    DELEGATE_RESEARCH_TOOL,
    DELEGATE_RESEARCH_TOOL_RESPONSE_API,
    DELEGATE_REVIEW_TOOL,
    DELEGATE_REVIEW_TOOL_RESPONSE_API,
    SUBAGENT_TOOL_NAMES,
    SUBAGENT_TOOLS,
    SUBAGENT_TOOLS_RESPONSE_API,
)

# Full toolset for Main Agent (4 primitives + 2 explicit subagent delegation tools)
MAIN_AGENT_TOOLS = ALL_TOOLS + SUBAGENT_TOOLS
MAIN_AGENT_TOOLS_RESPONSE_API = ALL_TOOLS_RESPONSE_API + SUBAGENT_TOOLS_RESPONSE_API

# Complete set of allowed tool names
TOOL_NAMES = {"read", "write", "edit", "bash"} | SUBAGENT_TOOL_NAMES



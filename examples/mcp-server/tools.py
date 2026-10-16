"""Tool implementations exposed by the MCP server.

Each tool is a callable that receives the JSON-RPC ``arguments`` object and
returns an MCP tool result payload of the shape::

    {"content": [{"type": "text", "text": "..."}], "isError": False}

Every tool also exposes a JSON Schema (draft 2020-12 subset) via
:data:`TOOL_DEFINITIONS`, which is what ``tools/list`` advertises to clients.

All diagnostic logging is emitted through :func:`logging` which the entrypoint
configures to target ``stderr``; nothing here ever prints to stdout.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Tuple

__all__ = [
    "TOOL_DEFINITIONS",
    "TOOL_REGISTRY",
    "ToolError",
    "system_metrics",
    "analyze_codebase",
    "ping_diagnostic",
    "list_tool_definitions",
    "call_tool",
    "text_result",
    "error_result",
]

logger = logging.getLogger("mcp.tools")

WORKSPACE_ROOT = Path.cwd()

# Directories that are noise for source statistics and would otherwise make the
# recursive walk explode on virtualenvs / VCS metadata / build output.
DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
        ".eggs",
    }
)

# Extensions considered "source code" for line counting purposes.
CODE_EXTENSIONS = frozenset(
    {
        ".py", ".pyi", ".pyx", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
        ".java", ".kt", ".kts", ".scala", ".go", ".rs", ".rb", ".php", ".c",
        ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".swift", ".m",
        ".mm", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".sql", ".lua", ".pl",
        ".r", ".jl", ".dart", ".vue", ".svelte", ".ex", ".exs", ".erl", ".hs",
        ".clj", ".cljs", ".groovy", ".gradle", ".tf", ".proto",
    }
)

MAX_WALK_ENTRIES = 200_000


class ToolError(Exception):
    """Raised by a tool to signal a recoverable, client-visible failure.

    The message is surfaced to the caller inside ``isError: true`` content
    rather than as a JSON-RPC protocol error.
    """

    def __init__(self, message: str, code: str = "TOOL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class ToolDefinition:
    """Static metadata describing a tool for ``tools/list``."""

    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DiagnosticReport:
    """Structured health-check payload returned by :func:`ping_diagnostic`."""

    status: str
    message: str
    timestamp: str
    server_name: str
    pid: int
    python_version: str
    workspace_root: str


def text_result(text: str) -> Dict[str, Any]:
    """Wrap a plain string in an MCP text-content result."""
    return {"content": [{"type": "text", "text": text}], "isError": False}


def error_result(text: str) -> Dict[str, Any]:
    """Wrap an error string in an MCP result flagged with ``isError``."""
    return {"content": [{"type": "text", "text": text}], "isError": True}


# ---------------------------------------------------------------------------
# Tool: system_metrics
# ---------------------------------------------------------------------------
def system_metrics(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Return platform, interpreter and workspace facts for the running host."""
    resolve_workspace = bool(arguments.get("resolve_workspace", False))

    workspace = WORKSPACE_ROOT
    if resolve_workspace:
        try:
            workspace = WORKSPACE_ROOT.resolve(strict=False)
        except OSError as exc:  # pragma: no cover - defensive
            raise ToolError(f"failed to resolve workspace root: {exc}", "WORKSPACE_ERROR") from exc

    lines: List[Tuple[str, str]] = [
        ("platform", platform.platform()),
        ("system", f"{platform.system()} {platform.release()}"),
        ("machine", platform.machine()),
        ("processor", platform.processor() or "unknown"),
        ("python_version", platform.python_version()),
        ("python_implementation", platform.python_implementation()),
        ("python_executable", sys.executable or "unknown"),
        ("pid", str(os.getpid())),
        ("workspace_root", str(workspace)),
        ("workspace_exists", str(workspace.is_dir())),
    ]

    width = max(len(key) for key, _ in lines)
    body = "\n".join(f"{key.ljust(width)} : {value}" for key, value in lines)
    return text_result(f"System metrics\n{'=' * (width + 3)}\n{body}")


# ---------------------------------------------------------------------------
# Tool: analyze_codebase
# ---------------------------------------------------------------------------
def analyze_codebase(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively count files and code lines under the workspace directory.

    Arguments (all optional):
        path: sub-path (relative to the workspace root) to analyse.
        include_hidden: count dotfiles / dot-directories too.
        extensions: explicit list of extensions to treat as code.
        max_entries: safety cap on walked entries.
    """
    raw_path = arguments.get("path") or "."
    if not isinstance(raw_path, str):
        raise ToolError("'path' must be a string", "INVALID_ARGUMENT")

    include_hidden = bool(arguments.get("include_hidden", False))

    raw_extensions = arguments.get("extensions")
    if raw_extensions is None:
        code_extensions = CODE_EXTENSIONS
    elif isinstance(raw_extensions, list):
        normalised = set()
        for item in raw_extensions:
            if not isinstance(item, str) or not item.strip():
                raise ToolError("'extensions' entries must be non-empty strings", "INVALID_ARGUMENT")
            ext = item.strip().lower()
            normalised.add(ext if ext.startswith(".") else f".{ext}")
        code_extensions = frozenset(normalised)
    else:
        raise ToolError("'extensions' must be an array of strings", "INVALID_ARGUMENT")

    raw_max_entries = arguments.get("max_entries", MAX_WALK_ENTRIES)
    if isinstance(raw_max_entries, bool) or not isinstance(raw_max_entries, int):
        raise ToolError("'max_entries' must be an integer", "INVALID_ARGUMENT")
    if raw_max_entries <= 0:
        raise ToolError("'max_entries' must be positive", "INVALID_ARGUMENT")

    target = (WORKSPACE_ROOT / raw_path).resolve(strict=False)
    root = WORKSPACE_ROOT.resolve(strict=False)

    # Confine traversal to the workspace to avoid unbounded / surprising walks.
    if target != root and root not in target.parents:
        raise ToolError(
            f"path escapes the workspace root: {raw_path!r}", "PATH_ESCAPE"
        )
    if not target.exists():
        raise ToolError(f"path does not exist: {raw_path!r}", "NOT_FOUND")
    if not target.is_dir():
        raise ToolError(f"path is not a directory: {raw_path!r}", "NOT_A_DIRECTORY")

    total_files = 0
    code_files = 0
    code_lines = 0
    total_bytes = 0
    truncated = False
    visited = 0
    extension_counts: Dict[str, int] = {}

    for current_dir, dirnames, filenames in os.walk(target, topdown=True, followlinks=False):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in DEFAULT_IGNORED_DIRS and (include_hidden or not d.startswith("."))
        ]

        for filename in filenames:
            visited += 1
            if visited > raw_max_entries:
                truncated = True
                break

            if not include_hidden and filename.startswith("."):
                continue

            file_path = Path(current_dir) / filename
            total_files += 1

            try:
                total_bytes += file_path.stat().st_size
            except OSError:
                logger.debug("stat failed for %s", file_path, exc_info=True)

            extension = file_path.suffix.lower()
            if extension not in code_extensions:
                continue

            code_files += 1
            extension_counts[extension] = extension_counts.get(extension, 0) + 1
            code_lines += _count_lines(file_path)

        if truncated:
            break

    top_extensions = sorted(
        extension_counts.items(), key=lambda item: (-item[1], item[0])
    )[:10]

    report_lines = [
        "Codebase analysis",
        "=================",
        f"workspace_root : {root}",
        f"target         : {target}",
        f"total_files    : {total_files}",
        f"code_files     : {code_files}",
        f"code_lines     : {code_lines}",
        f"total_bytes    : {total_bytes}",
        f"truncated      : {truncated}",
    ]
    if truncated:
        report_lines.append(f"note           : stopped after {raw_max_entries} entries")
    if top_extensions:
        report_lines.append("top_extensions :")
        for extension, count in top_extensions:
            report_lines.append(f"    {extension:<8} {count}")

    return text_result("\n".join(report_lines))


# ---------------------------------------------------------------------------
# Tool: ping_diagnostic
# ---------------------------------------------------------------------------
def ping_diagnostic(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Return a health-check report echoing ``message`` back to the caller.

    Arguments:
        message: Optional human-readable probe payload. Non-string values are
            coerced via :func:`str` so the tool never fails on odd input.
        timestamp: Optional ISO-8601 override; defaults to UTC now.
    """
    raw_message = arguments.get("message", "")
    if raw_message is None:
        message = ""
    elif isinstance(raw_message, str):
        message = raw_message
    else:
        message = str(raw_message)

    timestamp = datetime.now(timezone.utc).isoformat()

    report = DiagnosticReport(
        status="healthy",
        message=message,
        timestamp=timestamp,
        server_name="mcp-stdio-server",
        pid=os.getpid(),
        python_version=platform.python_version(),
        workspace_root=str(WORKSPACE_ROOT),
    )

    logger.debug("ping_diagnostic status=%s", report.status)
    # Structured JSON keeps the result machine-parseable by MCP clients while
    # the leading line stays human readable in transcript UIs.
    return text_result(
        f"Diagnostic: {report.status}\n"
        + json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)
    )


def _count_lines(file_path: Path) -> int:
    """Count text lines in ``file_path``; binary/undecodable files count as 0."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as handle:
            return sum(1 for _ in handle)
    except (UnicodeDecodeError, OSError):
        pass

    # Fall back to a permissive decode so ANSI/latin-1 sources still count.
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        logger.debug("line count failed for %s", file_path, exc_info=True)
        return 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS: Tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="system_metrics",
        description=(
            "Report host and runtime facts: OS platform, Python version and "
            "interpreter, process id, and the current workspace directory."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "resolve_workspace": {
                    "type": "boolean",
                    "description": "Resolve the workspace path to a canonical absolute path.",
                    "default": False,
                }
            },
            "additionalProperties": False,
        },
    ),
    ToolDefinition(
        name="analyze_codebase",
        description=(
            "Recursively walk the workspace directory and report the total number "
            "of files and the number of code lines across recognised source files."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Sub-path within the workspace to analyse (default: '.').",
                    "default": ".",
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include dotfiles and dot-directories.",
                    "default": False,
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override the set of code file extensions to count.",
                },
                "max_entries": {
                    "type": "integer",
                    "description": "Safety cap on the number of directory entries walked.",
                    "minimum": 1,
                },
            },
            "additionalProperties": False,
        },
    ),
    ToolDefinition(
        name="ping_diagnostic",
        description=(
            "Health-check probe. Echoes a caller supplied message and returns a "
            "diagnostic report carrying a UTC timestamp and status 'healthy'."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Arbitrary probe payload echoed back in the report.",
                    "default": "",
                }
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    ),
)

TOOL_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "system_metrics": system_metrics,
    "analyze_codebase": analyze_codebase,
    "ping_diagnostic": ping_diagnostic,
}


def list_tool_definitions() -> List[Dict[str, Any]]:
    """Return ``tools/list`` payload entries."""
    return [definition.to_dict() for definition in TOOL_DEFINITIONS]


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch ``tools/call`` to the registered implementation."""
    handler = TOOL_REGISTRY.get(name)
    if handler is None:
        raise ToolError(f"unknown tool: {name!r}", "UNKNOWN_TOOL")

    if not isinstance(arguments, dict):
        raise ToolError("tool arguments must be an object", "INVALID_ARGUMENT")

    try:
        return handler(arguments)
    except ToolError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert to a client-visible error
        logger.exception("tool %s failed", name)
        raise ToolError(f"internal error in tool {name!r}: {exc}", "INTERNAL_ERROR") from exc

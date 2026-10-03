"""Operations for file read, write, and edit tools (Pi-agent compatible)."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any


def read_file_op(
    path: str | Path,
    offset: int = 1,
    limit: int | None = 2000,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Read file content with line numbers and pagination."""
    base = Path(base_dir or Path.cwd()).resolve()
    target = (base / path).resolve()
    if not target.exists():
        return {
            "output": f"Error: File '{path}' not found.",
            "returncode": 1,
            "exception_info": "FileNotFound",
        }
    if target.is_dir():
        return {
            "output": f"Error: '{path}' is a directory, not a file.",
            "returncode": 1,
            "exception_info": "IsADirectoryError",
        }
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {
            "output": f"Error reading file '{path}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }

    lines = content.splitlines()
    total_lines = len(lines)
    start_idx = max(0, offset - 1)
    if limit is None:
        end_idx = total_lines
    else:
        end_idx = min(total_lines, start_idx + limit)

    selected_lines = lines[start_idx:end_idx]
    numbered = [f"{i + 1:6d} | {line}" for i, line in enumerate(selected_lines, start=start_idx)]
    header = f"[File: {path} | Total lines: {total_lines} | Showing lines {start_idx + 1}-{end_idx}]"
    output = header + "\n" + "\n".join(numbered)
    if end_idx < total_lines:
        output += f"\n[... {total_lines - end_idx} more lines truncated. Use offset={end_idx + 1} to continue reading ...]"
    return {"output": output, "returncode": 0, "exception_info": ""}


def write_file_op(
    path: str | Path,
    content: str,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Create or overwrite a file, creating parent directories automatically."""
    base = Path(base_dir or Path.cwd()).resolve()
    target = (base / path).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        lines_count = len(content.splitlines())
        return {
            "output": f"Successfully wrote {len(content)} characters ({lines_count} lines) to '{path}'.",
            "returncode": 0,
            "exception_info": "",
        }
    except Exception as e:
        return {
            "output": f"Error writing to '{path}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }


def edit_file_op(
    path: str | Path,
    edits: list[dict[str, str]],
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Apply surgical find-and-replace edits to a file, returning a unified diff."""
    base = Path(base_dir or Path.cwd()).resolve()
    target = (base / path).resolve()
    if not target.exists():
        return {
            "output": f"Error: File '{path}' not found.",
            "returncode": 1,
            "exception_info": "FileNotFound",
        }
    if target.is_dir():
        return {
            "output": f"Error: '{path}' is a directory, not a file.",
            "returncode": 1,
            "exception_info": "IsADirectoryError",
        }
    try:
        original_content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {
            "output": f"Error reading '{path}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }

    # Normalize line endings to LF for matching
    content = original_content.replace("\r\n", "\n")
    for i, edit in enumerate(edits, start=1):
        old_text = edit.get("oldText", "").replace("\r\n", "\n")
        new_text = edit.get("newText", "").replace("\r\n", "\n")
        if not old_text:
            return {
                "output": f"Error in edit #{i}: 'oldText' cannot be empty.",
                "returncode": 1,
                "exception_info": "EmptyOldText",
            }
        count = content.count(old_text)
        if count == 0:
            return {
                "output": (
                    f"Error in edit #{i}: 'oldText' not found in '{path}'.\n"
                    "Ensure the target code snippet matches the existing file content exactly, including whitespace and indentation."
                ),
                "returncode": 1,
                "exception_info": "OldTextNotFound",
            }
        if count > 1:
            return {
                "output": (
                    f"Error in edit #{i}: 'oldText' matched {count} times in '{path}'.\n"
                    "Please provide more surrounding context lines to make the replacement unique."
                ),
                "returncode": 1,
                "exception_info": "AmbiguousOldText",
            }
        content = content.replace(old_text, new_text, 1)

    # Generate unified diff
    diff_lines = list(
        difflib.unified_diff(
            original_content.replace("\r\n", "\n").splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    diff_text = "".join(diff_lines)

    # Preserve CRLF if original file had CRLF
    if "\r\n" in original_content:
        final_content = content.replace("\n", "\r\n")
    else:
        final_content = content

    try:
        target.write_text(final_content, encoding="utf-8")
        summary = f"Successfully applied {len(edits)} edit(s) to '{path}'.\n\n```diff\n{diff_text}```"
        return {"output": summary, "returncode": 0, "exception_info": ""}
    except Exception as e:
        return {
            "output": f"Error saving edited file '{path}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }

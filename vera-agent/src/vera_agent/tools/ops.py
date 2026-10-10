"""Operations for file read, write, and edit tools."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any


def validate_safe_path(
    path: str | Path,
    base_dir: Path | None = None,
    allowed_write_prefix: Path | str | None = None,
    is_write: bool = False,
    allow_external_read: bool = False,
) -> tuple[Path | None, str | None]:
    """Validate path safety against workspace boundary and optional write prefix restriction.

    Returns:
        (resolved_path, error_message). If error_message is not None, operation should be blocked.
    """
    base = Path(base_dir or Path.cwd()).resolve()
    """ Resolve the absolute path of the project root directory and the target file. """
    try:
        target = (base / path).resolve()
        """ Root directory/relative path --> absolute path """
    except Exception as e:
        return None, f"Invalid path syntax '{path}': {e}"

    # Reads may be explicitly allowed outside the project; writes never are.
    if not target.is_relative_to(base) and (is_write or not allow_external_read):
        return None, f"AccessDenied: Path '{path}' escapes workspace boundary '{base}'."

    # 2. Write restriction: if allowed_write_prefix is specified, writes must stay within it
    if is_write and allowed_write_prefix is not None:
        prefix = Path(allowed_write_prefix).resolve()
        if not target.is_relative_to(prefix):
            return None, (
                f"PermissionDenied: Write operation to '{path}' blocked. "
                f"Subagents are restricted to their designated scratchpad workspace: '{prefix}'."
            )

    return target, None


def read_file_op(
    path: str | Path,
    offset: int = 1,
    limit: int | None = 2000,
    base_dir: Path | None = None,
    allow_external_read: bool = False,
) -> dict[str, Any]:
    """Read file content with line numbers and pagination."""
    target, err = validate_safe_path(path, base_dir=base_dir, is_write=False, allow_external_read=allow_external_read)
    if err:
        return {
            "output": f"Error: {err}",
            "returncode": 1,
            "exception_info": "AccessDenied" if "AccessDenied" in err else "PathError",
        }
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
    allowed_write_prefix: Path | str | None = None,
) -> dict[str, Any]:
    """Create or overwrite a file, creating parent directories automatically."""
    target, err = validate_safe_path(
        path, base_dir=base_dir, allowed_write_prefix=allowed_write_prefix, is_write=True
    )
    if err:
        return {
            "output": f"Error: {err}",
            "returncode": 1,
            "exception_info": "PermissionDenied" if "PermissionDenied" in err else "AccessDenied",
        }
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
    allowed_write_prefix: Path | str | None = None,
) -> dict[str, Any]:
    """Apply surgical find-and-replace edits to a file, returning a unified diff."""
    target, err = validate_safe_path(
        path, base_dir=base_dir, allowed_write_prefix=allowed_write_prefix, is_write=True
    )
    if err:
        return {
            "output": f"Error: {err}",
            "returncode": 1,
            "exception_info": "PermissionDenied" if "PermissionDenied" in err else "AccessDenied",
        }
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

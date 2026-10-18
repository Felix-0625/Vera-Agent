"""AST-based code intelligence and syntax verification tools.

Adheres to Pi-agent minimalism and zero-dependency reliability:
- check_syntax_op: Pre-flight syntax validation using Python's built-in AST
- symbol_search_op: Fast AST symbol discovery (classes, methods, functions) across files
- find_references_op: Fast text/symbol occurrence search
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Literal


def check_syntax_op(code: str, filename: str = "<input>") -> tuple[bool, str]:
    """Validate Python code syntax without executing it.

    Returns:
        (is_valid, error_message_or_ok)
    """
    try:
        ast.parse(code, filename=filename)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"


def symbol_search_op(
    repo_path: Path | str,
    query: str,
    symbol_type: Literal["all", "class", "function"] = "all",
    max_results: int = 30,
) -> list[dict[str, Any]]:
    """Search for class, method, and function symbols across Python files in repo.

    Returns a list of dicts with name, type, path, line_number, and docstring preview.
    """
    root = Path(repo_path).resolve()
    results: list[dict[str, Any]] = []
    q_lower = query.lower()

    for path in root.rglob("*.py"):
        # Skip virtualenvs and hidden caches
        parts = path.parts
        if any(p.startswith(".") or p in ("venv", ".venv", "__pycache__", "build", "dist") for p in parts):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))
        except Exception:
            continue

        rel_path = str(path.relative_to(root))

        for node in ast.walk(tree):
            match = False
            item_type = None

            if isinstance(node, ast.ClassDef):
                if symbol_type in ("all", "class") and q_lower in node.name.lower():
                    match = True
                    item_type = "class"
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if symbol_type in ("all", "function") and q_lower in node.name.lower():
                    match = True
                    item_type = "function"

            if match and item_type:
                doc = ast.get_docstring(node) or ""
                doc_preview = doc.splitlines()[0][:80] if doc else ""
                results.append(
                    {
                        "name": getattr(node, "name", ""),
                        "type": item_type,
                        "path": rel_path,
                        "line": getattr(node, "lineno", 1),
                        "doc": doc_preview,
                    }
                )

                if len(results) >= max_results:
                    return results

    return results


def find_references_op(
    repo_path: Path | str,
    symbol_name: str,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """Find occurrences of a specific symbol across the codebase."""
    root = Path(repo_path).resolve()
    results: list[dict[str, Any]] = []
    pattern = re.compile(rf"\b{re.escape(symbol_name)}\b")

    for path in root.rglob("*.py"):
        parts = path.parts
        if any(p.startswith(".") or p in ("venv", ".venv", "__pycache__", "build", "dist") for p in parts):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel_path = str(path.relative_to(root))
        for line_no, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                results.append(
                    {
                        "path": rel_path,
                        "line": line_no,
                        "content": line.strip()[:100],
                    }
                )
                if len(results) >= max_results:
                    return results

    return results

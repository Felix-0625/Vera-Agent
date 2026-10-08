"""Tool 2: File tree exploration, content preview, AST syntax checking, and symbol search."""

from __future__ import annotations

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState
from vera_agent.tools.code_tools import check_syntax_op, symbol_search_op

logger = logging.getLogger("vera_server.files")

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return str(resolved_target).startswith(str(resolved_base))
    except Exception:
        return False


def _build_tree(curr_dir: Path, base_dir: Path, max_depth: int = 5, current_depth: int = 0) -> dict | None:
    if current_depth > max_depth or curr_dir.name in EXCLUDED_DIRS:
        return None

    try:
        children = []
        # Sort directories first, then files
        entries = sorted(curr_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        for entry in entries:
            if entry.name in EXCLUDED_DIRS or entry.name.startswith(".agents"):
                continue
            rel_path = str(entry.relative_to(base_dir)).replace("\\", "/")
            if entry.is_dir():
                sub_tree = _build_tree(entry, base_dir, max_depth, current_depth + 1)
                if sub_tree:
                    children.append(sub_tree)
            else:
                children.append({
                    "name": entry.name,
                    "path": rel_path,
                    "is_dir": False,
                    "size": entry.stat().st_size if entry.exists() else 0,
                })

        return {
            "name": curr_dir.name if current_depth > 0 else base_dir.name,
            "path": "" if current_depth == 0 else str(curr_dir.relative_to(base_dir)).replace("\\", "/"),
            "is_dir": True,
            "children": children,
        }
    except Exception as e:
        logger.warning("Error reading directory %s: %s", curr_dir, e)
        return None


async def get_files_tree(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.query_params.get("group_id")
    base = state.root_path
    if group_id and state.graph and group_id in state.graph.groups:
        base = state.graph.groups[group_id].worktree_path

    tree = _build_tree(base, base) or {"name": base.name, "path": "", "is_dir": True, "children": []}
    return JSONResponse(tree)


async def get_file_content(request: Request) -> JSONResponse:
    state = _get_state(request)
    file_rel_or_abs = request.query_params.get("path", "").strip()
    group_id = request.query_params.get("group_id")

    if not file_rel_or_abs:
        return JSONResponse({"error": "path parameter is required"}, status_code=400)

    base = state.root_path
    if group_id and state.graph and group_id in state.graph.groups:
        base = state.graph.groups[group_id].worktree_path

    target = (base / file_rel_or_abs) if not Path(file_rel_or_abs).is_absolute() else Path(file_rel_or_abs)
    if not _is_safe_path(base, target):
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)

    if not target.exists() or not target.is_file():
        return JSONResponse({"error": f"File '{file_rel_or_abs}' not found"}, status_code=404)

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = len(content.splitlines())
        return JSONResponse({
            "path": str(target.relative_to(base)).replace("\\", "/"),
            "name": target.name,
            "content": content,
            "lines": lines,
            "size": target.stat().st_size,
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to read file: {e}"}, status_code=500)


async def check_syntax(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    code = body.get("code", "")
    valid, msg = check_syntax_op(code)
    return JSONResponse({"valid": valid, "message": msg})


async def search_symbols(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    query = body.get("query", "")
    sym_type = body.get("symbol_type", "all")
    results = symbol_search_op(state.root_path, query=query, symbol_type=sym_type)
    return JSONResponse({"results": results})


file_routes = [
    Route("/api/files/tree", get_files_tree, methods=["GET"]),
    Route("/api/files/content", get_file_content, methods=["GET"]),
    Route("/api/code/check-syntax", check_syntax, methods=["POST"]),
    Route("/api/code/search-symbols", search_symbols, methods=["POST"]),
]

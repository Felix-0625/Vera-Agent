"""Project file explorer routes.

Routes: GET /api/files/tree, /api/files/content, /api/files/preview, /api/files/raw;
PUT /api/files/content, /api/files/excel; POST /api/code/check-syntax,
/api/code/search-symbols.

Paths are resolved against the bound project and checked to stay inside it.
This is an application-level path policy, not an OS sandbox.
"""

from __future__ import annotations

import logging
import mimetypes
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from vera_agent.server.routes.office_files import read_pptx_slides, read_xlsx, write_xlsx, xlsx_layout
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

EDITABLE_TEXT_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".py",
    ".pyw",
    ".yaml",
    ".yml",
    ".toml",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".json",
    ".jsonc",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".bat",
    ".cmd",
    ".html",
    ".htm",
    ".xml",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".sql",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".vue",
    ".svelte",
    ".graphql",
    ".gql",
    ".r",
}


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False


def _get_project_roots(state: ServerState, project_id: str | None) -> tuple[dict, list[Path]] | None:
    if not project_id:
        return None
    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return None
    raw_folders = project.get("folders") or [project.get("path", "")]
    roots = []
    for raw_folder in raw_folders:
        if not isinstance(raw_folder, str) or not raw_folder.strip():
            continue
        folder = Path(raw_folder).expanduser().resolve()
        if folder.is_dir() and folder not in roots:
            roots.append(folder)
    return (project, roots) if roots else None


def _resolve_file(
    state: ServerState,
    request: Request,
    path: str,
    group_id: str | None = None,
    project_id: str | None = None,
) -> tuple[Path, Path] | None:
    group_id = group_id or request.query_params.get("group_id")
    project_id = project_id or request.query_params.get("project_id")
    if not project_id and group_id and state.graph and group_id in state.graph.groups:
        base = Path(state.graph.groups[group_id].worktree_path).resolve()
        requested = Path(path)
        target = (base / requested) if not requested.is_absolute() else requested
        return (base, target.resolve()) if _is_safe_path(base, target) else None

    project_scope = _get_project_roots(state, project_id)
    roots = project_scope[1] if project_scope else ([state.root_path.resolve()] if not project_id else [])
    if not roots:
        return None

    normalized = path.replace("\\", "/")
    if normalized.startswith("@folder/"):
        parts = normalized.split("/", 2)
        if len(parts) < 2 or not parts[1].isdigit():
            return None
        index = int(parts[1])
        if index >= len(roots):
            return None
        base = roots[index]
        relative = parts[2] if len(parts) > 2 else ""
        target = (base / relative).resolve()
        return (base, target) if _is_safe_path(base, target) else None

    requested = Path(path)
    if requested.is_absolute():
        target = requested.resolve()
        base = next((root for root in roots if _is_safe_path(root, target)), None)
        return (base, target) if base else None

    base = roots[0]
    target = (base / requested).resolve()
    return (base, target) if _is_safe_path(base, target) else None


def _build_tree(
    curr_dir: Path,
    base_dir: Path,
    max_depth: int = 5,
    current_depth: int = 0,
    path_prefix: str = "",
) -> dict | None:
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
            rel_path = f"{path_prefix}/{rel_path}".strip("/") if path_prefix else rel_path
            if entry.is_dir():
                sub_tree = _build_tree(entry, base_dir, max_depth, current_depth + 1, path_prefix)
                if sub_tree:
                    children.append(sub_tree)
            else:
                children.append(
                    {
                        "name": entry.name,
                        "path": rel_path,
                        "is_dir": False,
                        "size": entry.stat().st_size if entry.exists() else 0,
                    }
                )

        return {
            "name": curr_dir.name if current_depth > 0 else base_dir.name,
            "path": path_prefix
            if current_depth == 0
            else f"{path_prefix}/{str(curr_dir.relative_to(base_dir)).replace(chr(92), '/')}".strip("/"),
            "is_dir": True,
            "children": children,
        }
    except Exception as e:
        logger.warning("Error reading directory %s: %s", curr_dir, e)
        return None


async def get_files_tree(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.query_params.get("group_id")
    project_id = request.query_params.get("project_id")
    base = state.root_path
    if not project_id and group_id and state.graph and group_id in state.graph.groups:
        base = state.graph.groups[group_id].worktree_path
        tree = _build_tree(base, base)
        return JSONResponse(tree or {"name": base.name, "path": "", "is_dir": True, "children": []})

    project_scope = _get_project_roots(state, project_id)
    if project_id and not project_scope:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    if project_scope:
        project, roots = project_scope
        if len(roots) > 1:
            children = [
                tree
                for index, folder in enumerate(roots)
                if (tree := _build_tree(folder, folder, path_prefix=f"@folder/{index}")) is not None
            ]
            tree = {"name": project.get("name") or roots[0].name, "path": "", "is_dir": True, "children": children}
        else:
            base = roots[0]
            tree = _build_tree(base, base)
    else:
        tree = _build_tree(base, base)
    tree = tree or {"name": base.name, "path": "", "is_dir": True, "children": []}
    return JSONResponse(tree)


async def get_file_content(request: Request) -> JSONResponse:
    state = _get_state(request)
    file_rel_or_abs = request.query_params.get("path", "").strip()
    group_id = request.query_params.get("group_id")

    if not file_rel_or_abs:
        return JSONResponse({"error": "path parameter is required"}, status_code=400)

    resolved = _resolve_file(state, request, file_rel_or_abs, group_id)
    if resolved is None:
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)
    base, target = resolved

    if not target.exists() or not target.is_file():
        return JSONResponse({"error": f"File '{file_rel_or_abs}' not found"}, status_code=404)

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = len(content.splitlines())
        return JSONResponse(
            {
                "path": str(target.relative_to(base)).replace("\\", "/"),
                "name": target.name,
                "content": content,
                "lines": lines,
                "size": target.stat().st_size,
            }
        )
    except Exception as e:
        return JSONResponse({"error": f"Failed to read file: {e}"}, status_code=500)


async def get_file_preview(request: Request) -> JSONResponse:
    state = _get_state(request)
    resolved = _resolve_file(state, request, request.query_params.get("path", "").strip())
    if resolved is None:
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)
    _, target = resolved
    if not target.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    suffix = target.suffix.lower()
    detected_type = mimetypes.guess_type(target.name)[0] or ""
    if suffix == ".pdf":
        return JSONResponse({"kind": "pdf", "url": _raw_file_url(request, target)})
    if detected_type.startswith("image/") or suffix in {".avif", ".heic", ".heif", ".tif", ".tiff", ".apng"}:
        return JSONResponse({"kind": "pdf" if suffix == ".pdf" else "image", "url": _raw_file_url(request, target)})
    if suffix in {".xlsx", ".xlsm"}:
        try:
            with zipfile.ZipFile(target) as archive:
                sheet_defs, _ = xlsx_layout(archive)
            return JSONResponse(
                {"kind": "excel", "sheets": read_xlsx(target), "sheet_names": [sheet["name"] for sheet in sheet_defs]}
            )
        except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, ValueError) as exc:
            return JSONResponse({"error": f"无法预览 Excel 文件: {exc}"}, status_code=400)
    if suffix == ".pptx":
        try:
            return JSONResponse({"kind": "ppt", "slides": read_pptx_slides(target)})
        except (OSError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
            return JSONResponse({"error": f"无法预览 PowerPoint 文件: {exc}"}, status_code=400)
    if suffix in {".ppt", ".xls", ".doc", ".docx"}:
        return JSONResponse(
            {
                "kind": "unsupported",
                "message": "此旧版或非目标格式暂不支持内嵌预览。",
                "url": _raw_file_url(request, target),
            }
        )
    try:
        raw = target.read_bytes()
        if b"\x00" in raw:
            return JSONResponse(
                {"kind": "unsupported", "message": "二进制文件不支持文本预览。", "url": _raw_file_url(request, target)}
            )
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            return JSONResponse(
                {
                    "kind": "unsupported",
                    "message": "该文件不是 UTF-8 文本，无法安全地作为文本预览。",
                    "url": _raw_file_url(request, target),
                }
            )
        return JSONResponse({"kind": "text", "content": content})
    except OSError as exc:
        return JSONResponse({"error": f"无法预览文件: {exc}"}, status_code=400)


def _raw_file_url(request: Request, target: Path) -> str:
    query = {"path": str(target)}
    group_id = request.query_params.get("group_id")
    if group_id:
        query["group_id"] = group_id
    project_id = request.query_params.get("project_id")
    if project_id:
        query["project_id"] = project_id
    return f"/api/files/raw?{urlencode(query)}"


async def get_raw_file(request: Request) -> FileResponse | JSONResponse:
    state = _get_state(request)
    resolved = _resolve_file(state, request, request.query_params.get("path", "").strip())
    if resolved is None:
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)
    _, target = resolved
    if not target.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        target,
        media_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream",
        filename=target.name,
        content_disposition_type="inline",
    )


async def save_file_content(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    path = str(body.get("path", "")).strip()
    resolved = _resolve_file(state, request, path, body.get("group_id"), body.get("project_id"))
    if resolved is None:
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)
    _, target = resolved
    if not target.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    if target.suffix.lower() not in EDITABLE_TEXT_SUFFIXES and target.name.lower() != ".gitignore":
        return JSONResponse({"error": "此文件类型不支持文本编辑"}, status_code=415)
    content = body.get("content")
    if not isinstance(content, str):
        return JSONResponse({"error": "content must be a string"}, status_code=400)
    target.write_text(content, encoding="utf-8", newline="")
    return JSONResponse({"status": "saved", "path": str(target)})


async def save_excel_file(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    resolved = _resolve_file(
        state, request, str(body.get("path", "")).strip(), body.get("group_id"), body.get("project_id")
    )
    if resolved is None:
        return JSONResponse({"error": "Access denied: Path is outside workspace root"}, status_code=403)
    _, target = resolved
    sheets = body.get("sheets")
    if not target.is_file() or target.suffix.lower() not in {".xlsx", ".xlsm"}:
        return JSONResponse({"error": "Excel file not found or unsupported"}, status_code=404)
    if not isinstance(sheets, list):
        return JSONResponse({"error": "sheets must be an array"}, status_code=400)
    try:
        write_xlsx(target, sheets)
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, ValueError) as exc:
        return JSONResponse({"error": f"无法保存 Excel 文件: {exc}"}, status_code=400)
    return JSONResponse({"status": "saved", "path": str(target)})


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
    Route("/api/files/preview", get_file_preview, methods=["GET"]),
    Route("/api/files/raw", get_raw_file, methods=["GET"]),
    Route("/api/files/content", save_file_content, methods=["PUT"]),
    Route("/api/files/excel", save_excel_file, methods=["PUT"]),
    Route("/api/code/check-syntax", check_syntax, methods=["POST"]),
    Route("/api/code/search-symbols", search_symbols, methods=["POST"]),
]

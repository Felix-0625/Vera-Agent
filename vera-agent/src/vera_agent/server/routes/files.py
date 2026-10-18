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
import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
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


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref.upper())
    if not letters:
        return 0
    value = 0
    for char in letters.group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def _xlsx_layout(archive: zipfile.ZipFile) -> tuple[list[dict], list[str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets = []
    for sheet in workbook.iter():
        if sheet.tag.endswith("}sheet"):
            rel_id = next((value for key, value in sheet.attrib.items() if key.endswith("}id")), "")
            target = rel_targets.get(rel_id, "")
            target_path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
            sheets.append({"name": sheet.attrib.get("name", "Sheet"), "path": target_path})
    shared_strings = []
    if "xl/sharedStrings.xml" in archive.namelist():
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in shared_root:
            shared_strings.append("".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")))
    return sheets, shared_strings


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = next((child.text or "" for child in cell if child.tag.endswith("}v")), "")
    if kind == "s" and value:
        return shared[int(value)] if int(value) < len(shared) else ""
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t"))
    return value


def _read_xlsx(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        sheet_defs, shared = _xlsx_layout(archive)
        result = []
        for sheet in sheet_defs:
            root = ET.fromstring(archive.read(sheet["path"]))
            rows = []
            for row in root.iter():
                if not row.tag.endswith("}row"):
                    continue
                values: list[str] = []
                for cell in row:
                    if not cell.tag.endswith("}c"):
                        continue
                    index = _column_index(cell.attrib.get("r", ""))
                    while len(values) <= index:
                        values.append("")
                    kind = cell.attrib.get("t")
                    value = next((child.text or "" for child in cell if child.tag.endswith("}v")), "")
                    if kind == "s" and value:
                        value = shared[int(value)] if int(value) < len(shared) else ""
                    elif kind == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t"))
                    values[index] = value
                row_number = int(row.attrib.get("r", str(len(rows) + 1)))
                while len(rows) < row_number:
                    rows.append([])
                rows[row_number - 1] = values
            result.append({"name": sheet["name"], "rows": rows})
        return result


def _write_xlsx(target: Path, sheets: list[dict]) -> None:
    namespaces = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ET.register_namespace("", namespaces["main"])
    with zipfile.ZipFile(target) as source:
        sheet_defs, shared = _xlsx_layout(source)
        replacements: dict[str, bytes] = {}
        for sheet_def, edited in zip(sheet_defs, sheets):
            root = ET.fromstring(source.read(sheet_def["path"]))
            sheet_data = next((node for node in root.iter() if node.tag.endswith("}sheetData")), None)
            if sheet_data is None:
                continue
            existing_rows = {int(row.attrib.get("r", "0")): row for row in sheet_data if row.tag.endswith("}row")}
            for row_index, values in enumerate(edited.get("rows", []), start=1):
                row = existing_rows.get(row_index)
                if row is None:
                    row = ET.Element(f"{{{namespaces['main']}}}row", {"r": str(row_index)})
                    sheet_data.append(row)
                existing_cells = {cell.attrib.get("r"): cell for cell in row if cell.tag.endswith("}c")}
                for column_index, raw in enumerate(values):
                    value = str(raw) if raw is not None else ""
                    cell_ref = ""
                    number = column_index + 1
                    while number:
                        number, remainder = divmod(number - 1, 26)
                        cell_ref = chr(65 + remainder) + cell_ref
                    cell_ref += str(row_index)
                    cell = existing_cells.get(cell_ref)
                    if cell is not None and _cell_value(cell, shared) == value:
                        continue
                    if cell is None and not value:
                        continue
                    if cell is None:
                        cell = ET.Element(f"{{{namespaces['main']}}}c", {"r": cell_ref})
                        row.append(cell)
                    for child in list(cell):
                        cell.remove(child)
                    cell.attrib.pop("t", None)
                    if value.startswith("="):
                        ET.SubElement(cell, f"{{{namespaces['main']}}}f").text = value[1:]
                    elif value:
                        try:
                            float(value)
                            is_number = True
                        except ValueError:
                            is_number = False
                        if is_number:
                            ET.SubElement(cell, f"{{{namespaces['main']}}}v").text = value
                        else:
                            cell.set("t", "inlineStr")
                            inline = ET.SubElement(cell, f"{{{namespaces['main']}}}is")
                            text_node = ET.SubElement(inline, f"{{{namespaces['main']}}}t")
                            if value != value.strip():
                                text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                            text_node.text = value
            replacements[sheet_def["path"]] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=target.suffix, delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as output:
                for item in source.infolist():
                    output.writestr(item, replacements.get(item.filename, source.read(item.filename)))
            os.replace(temp_path, target)
        finally:
            temp_path.unlink(missing_ok=True)


def _pptx_slides(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        slide_paths = sorted(
            (item for item in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", item)),
            key=lambda item: int(re.search(r"slide(\d+)", item).group(1)),
        )
        slides = []
        for slide_path in slide_paths:
            root = ET.fromstring(archive.read(slide_path))
            text = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
            slides.append({"text": "\n".join(text)})
        return slides


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
                sheet_defs, _ = _xlsx_layout(archive)
            return JSONResponse(
                {"kind": "excel", "sheets": _read_xlsx(target), "sheet_names": [sheet["name"] for sheet in sheet_defs]}
            )
        except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, ValueError) as exc:
            return JSONResponse({"error": f"无法预览 Excel 文件: {exc}"}, status_code=400)
    if suffix == ".pptx":
        try:
            return JSONResponse({"kind": "ppt", "slides": _pptx_slides(target)})
        except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
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
        _write_xlsx(target, sheets)
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

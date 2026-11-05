"""Read and edit Office Open XML files (.xlsx, .pptx) for the file preview pane.

Only the pieces the UI needs: sheet cells as text grids, slide text, and writing edited cells back into an
existing workbook. XML from user-opened files is parsed with ``defusedxml`` (no entity expansion); elements
we build ourselves use the standard library.
"""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def _tag(name: str) -> str:
    return f"{{{SPREADSHEET_NS}}}{name}"


def _column_index(cell_ref: str) -> int:
    """Zero-based column of a cell reference such as ``AB12``."""
    letters = re.match(r"[A-Z]+", cell_ref.upper())
    if not letters:
        return 0
    value = 0
    for char in letters.group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def _column_letters(index: int) -> str:
    """Inverse of ``_column_index``: ``0 -> A``, ``27 -> AB``."""
    letters = ""
    number = index + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def xlsx_layout(archive: zipfile.ZipFile) -> tuple[list[dict], list[str]]:
    """Return ``([{name, path}, ...], shared_strings)`` for a workbook."""
    workbook = SafeET.fromstring(archive.read("xl/workbook.xml"))
    rels = SafeET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
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
        shared_root = SafeET.fromstring(archive.read("xl/sharedStrings.xml"))
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


def read_xlsx(path: Path) -> list[dict]:
    """Return ``[{name, rows}]`` where ``rows`` is a list of string lists (empty rows kept)."""
    with zipfile.ZipFile(path) as archive:
        sheet_defs, shared = xlsx_layout(archive)
        result = []
        for sheet in sheet_defs:
            root = SafeET.fromstring(archive.read(sheet["path"]))
            rows: list[list[str]] = []
            for row in root.iter():
                if not row.tag.endswith("}row"):
                    continue
                values: list[str] = []
                for cell in row:
                    if not cell.tag.endswith("}c"):
                        continue
                    index = _column_index(cell.attrib.get("r", ""))
                    values.extend([""] * (index + 1 - len(values)))
                    values[index] = _cell_value(cell, shared)
                row_number = int(row.attrib.get("r", str(len(rows) + 1)))
                rows.extend([] for _ in range(row_number - len(rows)))
                rows[row_number - 1] = values
            result.append({"name": sheet["name"], "rows": rows})
        return result


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _write_cell(cell: ET.Element, value: str) -> None:
    """Replace ``cell`` content: formula for ``=...``, number as-is, anything else as an inline string."""
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)
    if value.startswith("="):
        ET.SubElement(cell, _tag("f")).text = value[1:]
    elif _is_number(value):
        ET.SubElement(cell, _tag("v")).text = value
    elif value:
        cell.set("t", "inlineStr")
        text_node = ET.SubElement(ET.SubElement(cell, _tag("is")), _tag("t"))
        if value != value.strip():
            text_node.set(f"{{{XML_NS}}}space", "preserve")
        text_node.text = value


def _apply_edits(sheet_data: ET.Element, edited_rows: list[list], shared: list[str]) -> None:
    existing_rows = {int(row.attrib.get("r", "0")): row for row in sheet_data if row.tag.endswith("}row")}
    for row_index, values in enumerate(edited_rows, start=1):
        row = existing_rows.get(row_index)
        if row is None:
            row = ET.Element(_tag("row"), {"r": str(row_index)})
            sheet_data.append(row)
        existing_cells = {cell.attrib.get("r"): cell for cell in row if cell.tag.endswith("}c")}
        for column_index, raw in enumerate(values):
            value = str(raw) if raw is not None else ""
            cell_ref = f"{_column_letters(column_index)}{row_index}"
            cell = existing_cells.get(cell_ref)
            if cell is not None and _cell_value(cell, shared) == value:
                continue
            if cell is None:
                if not value:
                    continue
                cell = ET.Element(_tag("c"), {"r": cell_ref})
                row.append(cell)
            _write_cell(cell, value)


def write_xlsx(target: Path, sheets: list[dict]) -> None:
    """Write edited cell values into ``target`` and atomically replace the file."""
    ET.register_namespace("", SPREADSHEET_NS)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=target.suffix, delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with zipfile.ZipFile(target) as source, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as output:
            sheet_defs, shared = xlsx_layout(source)
            replacements: dict[str, bytes] = {}
            # The UI may send fewer sheets than the workbook has; extra workbook sheets stay untouched.
            for sheet_def, edited in zip(sheet_defs, sheets):  # noqa: B905
                root = SafeET.fromstring(source.read(sheet_def["path"]))
                sheet_data = next((node for node in root.iter() if node.tag.endswith("}sheetData")), None)
                if sheet_data is None:
                    continue
                _apply_edits(sheet_data, edited.get("rows", []), shared)
                replacements[sheet_def["path"]] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            for item in source.infolist():
                output.writestr(item, replacements.get(item.filename, source.read(item.filename)))
        # Both archives are closed here: Windows refuses to replace a file that is still open.
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)


def read_pptx_slides(path: Path) -> list[dict]:
    """Return ``[{text}]`` with each slide's text runs joined by newlines, in slide order."""
    with zipfile.ZipFile(path) as archive:
        slide_paths = sorted(
            (item for item in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", item)),
            key=lambda item: int(re.search(r"slide(\d+)", item).group(1)),
        )
        slides = []
        for slide_path in slide_paths:
            root = SafeET.fromstring(archive.read(slide_path))
            text = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
            slides.append({"text": "\n".join(text)})
        return slides

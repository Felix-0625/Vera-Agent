"""Reading, editing and re-reading .xlsx cells and reading .pptx slide text."""

import zipfile
from pathlib import Path

from vera_agent.server.routes.office_files import (
    _column_index,
    _column_letters,
    read_pptx_slides,
    read_xlsx,
    write_xlsx,
)

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def make_workbook(path: Path) -> None:
    """A minimal one-sheet workbook: A1 is a shared string, B1 a number."""
    files = {
        "xl/workbook.xml": f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/sharedStrings.xml": f'<sst xmlns="{NS}"><si><t>name</t></si></sst>',
        "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{NS}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>5</v></c></row></sheetData></worksheet>',
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_column_letters_round_trip():
    for index in (0, 1, 25, 26, 27, 701, 702):
        assert _column_index(f"{_column_letters(index)}1") == index


def test_read_workbook_resolves_shared_strings_and_numbers(tmp_path):
    make_workbook(tmp_path / "book.xlsx")
    assert read_xlsx(tmp_path / "book.xlsx") == [{"name": "Data", "rows": [["name", "5"]]}]


def test_edited_cells_survive_a_write_and_read(tmp_path):
    path = tmp_path / "book.xlsx"
    make_workbook(path)

    write_xlsx(path, [{"name": "Data", "rows": [["renamed", "7", "=A1&B1"], ["", " padded ", "text"]]}])

    rows = read_xlsx(path)[0]["rows"]
    assert rows[0][:2] == ["renamed", "7"]
    assert rows[1] == ["", " padded ", "text"]
    sheet_xml = zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml").decode()
    assert "<f>A1&amp;B1</f>" in sheet_xml
    assert 'xml:space="preserve"' in sheet_xml


def test_unchanged_cells_are_left_alone(tmp_path):
    path = tmp_path / "book.xlsx"
    make_workbook(path)
    write_xlsx(path, [{"name": "Data", "rows": [["name", "5"]]}])
    # A1 still points at the shared string table instead of being rewritten inline.
    assert 't="s"' in zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml").decode()


def test_pptx_slides_are_read_in_numeric_order(tmp_path):
    path = tmp_path / "deck.pptx"
    with zipfile.ZipFile(path, "w") as archive:
        for number in (10, 2, 1):
            archive.writestr(
                f"ppt/slides/slide{number}.xml",
                f'<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>slide {number}</a:t></p:sld>',
            )
    assert [slide["text"] for slide in read_pptx_slides(path)] == ["slide 1", "slide 2", "slide 10"]

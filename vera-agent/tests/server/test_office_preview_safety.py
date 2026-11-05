"""Opening a hostile .xlsx/.pptx must fail with a 400, not expand XML entities or crash the API."""

import zipfile

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app

BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
    "<root>&b;&b;&b;&b;</root>"
)


@pytest.mark.parametrize(
    ("name", "member"),
    [("evil.xlsx", "xl/workbook.xml"), ("evil.pptx", "ppt/slides/slide1.xml")],
)
def test_entity_expansion_in_office_files_is_rejected(tmp_path, name, member):
    with zipfile.ZipFile(tmp_path / name, "w") as archive:
        archive.writestr(member, BILLION_LAUGHS)
    client = TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")

    response = client.get("/api/files/preview", params={"path": name})

    assert response.status_code == 400

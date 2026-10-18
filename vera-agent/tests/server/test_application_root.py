"""The application data folder is not recorded as a project when the API starts without a repo_root."""

import json
from pathlib import Path

import pytest

from vera_agent.server.state import ServerState


def test_default_startup_directory_is_not_added_to_project_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    state = ServerState()
    assert state.load_json_config("projects_history.json", {"projects": []})["projects"] == []

    project = tmp_path / "real-project"
    project.mkdir()
    state.init_workspace(project, project_name="Real project")
    history = json.loads((tmp_path / ".agents" / "projects_history.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in history["projects"]] == ["Real project"]


def test_explicit_repo_root_is_still_recorded(tmp_path: Path):
    state = ServerState(repo_root=tmp_path)
    paths = [item["path"] for item in state.load_json_config("projects_history.json", {"projects": []})["projects"]]
    assert paths == [str(tmp_path.resolve())]

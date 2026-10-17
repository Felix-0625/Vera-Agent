from pathlib import Path

from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.session.thread import ThreadSession


def _prepare_app(tmp_path: Path):
    app_root = tmp_path / "app"
    first_project = tmp_path / "first-project"
    second_project = tmp_path / "second-project"
    app_root.mkdir()
    first_project.mkdir()
    second_project.mkdir()

    app = create_app(repo_root=app_root)
    state = app.state.server_state
    state.init_workspace(first_project, project_id="project-one", project_name="First project")
    state.init_workspace(second_project, project_id="project-two", project_name="Second project")
    return app, app_root, first_project, second_project


def test_taskboard_crud_is_persistent_and_project_scoped(tmp_path: Path):
    app, app_root, first_project, _ = _prepare_app(tmp_path)
    client = TestClient(app)

    created = client.post("/api/taskboard/tasks", json={
        "project_id": "project-one",
        "title": "Review the taskboard integration",
        "description": "Keep the issue linked to this project.",
        "labels": ["review", "backend"],
    })
    assert created.status_code == 201
    item = created.json()["item"]
    assert item["identifier"].startswith("VA-")
    assert item["status"] == "todo"
    assert item["labels"] == ["review", "backend"]

    changed = client.patch(f"/api/taskboard/tasks/{item['id']}", json={
        "version": item["version"],
        "status": "in_progress",
        "priority": "high",
    })
    assert changed.status_code == 200
    assert changed.json()["item"]["status"] == "in_progress"
    assert changed.json()["item"]["version"] == item["version"] + 1

    stale = client.patch(f"/api/taskboard/tasks/{item['id']}", json={
        "version": item["version"],
        "title": "Stale write",
    })
    assert stale.status_code == 409

    assert client.get("/api/taskboard/tasks", params={"project_id": "project-one"}).json()["items"][0]["id"] == item["id"]
    assert client.get("/api/taskboard/tasks", params={"project_id": "project-two"}).json()["items"] == []
    assert (app_root / ".agents" / "taskboard.sqlite").is_file()
    assert not (first_project / ".agents" / "taskboard.sqlite").exists()

    archived = client.delete(f"/api/taskboard/tasks/{item['id']}")
    assert archived.status_code == 200
    assert client.get("/api/taskboard/tasks", params={"project_id": "project-one"}).json()["items"] == []


def test_taskboard_rejects_invalid_fields_and_cross_project_conversations(tmp_path: Path):
    app, _, _, second_project = _prepare_app(tmp_path)
    client = TestClient(app)

    invalid_status = client.post("/api/taskboard/tasks", json={
        "project_id": "project-one",
        "title": "Invalid",
        "status": {"unexpected": "object"},
    })
    assert invalid_status.status_code == 400

    created = client.post("/api/taskboard/tasks", json={"project_id": "project-one", "title": "Cross-project link"})
    assert created.status_code == 201
    item = created.json()["item"]

    other_session = ThreadSession(
        thread_id="thread_from_other_project",
        project_id="project-two",
        metadata={"project_root": str(second_project)},
    )
    other_session.save(second_project / ".agents" / "sessions" / "thread_from_other_project.json")

    linked = client.patch(f"/api/taskboard/tasks/{item['id']}", json={
        "version": item["version"],
        "thread_id": "thread_from_other_project",
    })
    assert linked.status_code == 400

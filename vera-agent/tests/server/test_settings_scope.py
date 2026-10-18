"""Model and permission settings are stored at application scope, not per project."""

from vera_agent.server.state import ServerState


def test_model_and_permission_settings_remain_application_scoped(tmp_path):
    app_root = tmp_path / "application"
    first_project = tmp_path / "first-project"
    second_project = tmp_path / "second-project"
    first_project.mkdir()
    second_project.mkdir()

    state = ServerState(repo_root=app_root)
    state.init_workspace(first_project, project_id="first")
    state.save_json_config("models_config.json", {"models": [{"id": "global-model"}]})
    state.save_json_config("permissions_config.json", {"default_mode": "human"})

    state.init_workspace(second_project, project_id="second")

    assert state.load_json_config("models_config.json", {}) == {"models": [{"id": "global-model"}]}
    assert state.load_json_config("permissions_config.json", {}) == {"default_mode": "human"}
    assert (first_project / ".agents" / "models_config.json").exists() is False
    assert (second_project / ".agents" / "permissions_config.json").exists() is False

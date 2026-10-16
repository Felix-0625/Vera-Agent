from vera_agent.server.model_profile import resolve_model_profile


class ConfigState:
    def __init__(self, models):
        self.models = models

    def load_json_config(self, name, default):
        assert name == "models_config.json"
        return {"models": self.models}


def _model(model_id, name, **extra):
    return {"id": model_id, "name": name, "provider": "deepseek", "base_url": "https://example.invalid/v1", "api_key": "configured-key", **extra}


def test_missing_selection_uses_only_enabled_configured_model():
    profile = resolve_model_profile(ConfigState([_model("cfg_1", "deepseek-chat")]))

    assert profile["name"] == "deepseek/deepseek-chat"
    assert profile["model_kwargs"]["api_key"] == "configured-key"
    assert profile["config"]["id"] == "cfg_1"


def test_missing_selection_requires_default_when_multiple_models_enabled():
    state = ConfigState([_model("cfg_1", "one"), _model("cfg_2", "two")])

    try:
        resolve_model_profile(state)
    except ValueError as error:
        assert "No default model" in str(error)
    else:
        raise AssertionError("ambiguous model configuration must not fall back to environment credentials")


def test_unknown_or_disabled_selection_is_rejected():
    state = ConfigState([_model("cfg_1", "one"), _model("cfg_2", "two", enabled=False)])

    for requested, expected in (("missing", "not found"), ("cfg_2", "disabled")):
        try:
            resolve_model_profile(state, requested)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError(f"{requested} must be rejected")


def test_missing_selection_uses_explicit_enabled_default():
    profile = resolve_model_profile(ConfigState([
        _model("cfg_1", "one"),
        _model("cfg_2", "two", is_default=True),
    ]))

    assert profile["config"]["id"] == "cfg_2"
    assert profile["name"] == "deepseek/two"


def test_model_id_takes_precedence_over_ambiguous_legacy_name():
    profile = resolve_model_profile(ConfigState([
        _model("same-name", "first"),
        _model("cfg_2", "same-name"),
    ]), "same-name")

    assert profile["config"]["id"] == "same-name"

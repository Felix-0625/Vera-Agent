"""Fixtures local to this regression suite."""

from pathlib import Path

import pytest
import yaml

from .helpers import (
    make_response_api_model,
    make_tc_model,
    make_text_model,
)


@pytest.fixture
def default_config():
    """Load default agent config from config/default.yaml"""
    config_path = Path("src/vera_agent/config/default.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["agent"]


@pytest.fixture
def toolcall_config():
    """Load toolcall agent config from config/mini.yaml"""
    config_path = Path("src/vera_agent/config/mini.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["agent"]


@pytest.fixture(params=["text", "toolcall", "response_api"])
def model_factory(request, default_config, toolcall_config):
    """Parametrized fixture that returns (factory_fn, config) for all three model types."""
    if request.param == "text":
        return make_text_model, default_config
    elif request.param == "toolcall":
        return make_tc_model, toolcall_config
    else:  # response_api
        return make_response_api_model, toolcall_config

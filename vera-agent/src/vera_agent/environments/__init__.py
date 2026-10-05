"""Environment implementations for mini-SWE-agent."""

import copy
import importlib

from vera_agent import Environment

_ENVIRONMENT_MAPPING = {
    "docker": "vera_agent.environments.docker.DockerEnvironment",
    "singularity": "vera_agent.environments.singularity.SingularityEnvironment",
    "local": "vera_agent.environments.local.LocalEnvironment",
    "swerex_docker": "vera_agent.environments.extra.swerex_docker.SwerexDockerEnvironment",
    "swerex_modal": "vera_agent.environments.extra.swerex_modal.SwerexModalEnvironment",
    "bubblewrap": "vera_agent.environments.extra.bubblewrap.BubblewrapEnvironment",
    "contree": "vera_agent.environments.extra.contree.ContreeEnvironment",
}


def get_environment_class(spec: str) -> type[Environment]:
    full_path = _ENVIRONMENT_MAPPING.get(spec, spec)
    try:
        module_name, class_name = full_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError):
        msg = f"Unknown environment type: {spec} (resolved to {full_path}, available: {_ENVIRONMENT_MAPPING})"
        raise ValueError(msg)


def get_environment(config: dict, *, default_type: str = "") -> Environment:
    config = copy.deepcopy(config)
    environment_class = config.pop("environment_class", default_type)
    return get_environment_class(environment_class)(**config)

"""Shared helpers for tests that drive `POST /api/chat/stream` with a scripted model."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

from vera_agent.models.litellm_model import LitellmModel

TEST_MODEL_ID = "m1"


def make_chat_repo(root: Path) -> Path:
    """A committed git repository with one configured (never called) model."""
    root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for args in (["init", "-b", "main"], ["config", "user.name", "T"], ["config", "user.email", "t@x.local"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=env)
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, env=env)
    config_dir = root / ".agents"
    config_dir.mkdir(exist_ok=True)
    model = {
        "id": TEST_MODEL_ID,
        "name": "deepseek/deepseek-chat",
        "provider": "deepseek",
        "api_key": "x",
        "enabled": True,
    }
    (config_dir / "models_config.json").write_text(json.dumps({"models": [model]}), encoding="utf-8")
    return root


def set_permissions(repo: Path, mode: str, **extra: Any) -> None:
    config = {"default_mode": mode, "approval_actions": ["terminal", "edit", "create"], **extra}
    (repo / ".agents" / "permissions_config.json").write_text(json.dumps(config), encoding="utf-8")


def parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in text.split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: ") and lines[1].startswith("data: "):
            events.append((lines[0][7:], json.loads(lines[1][6:])))
    return events


def reply(content: str, *actions: dict[str, Any]) -> dict[str, Any]:
    """One scripted assistant message with the given parsed actions."""
    return {"content": content, "extra": {"actions": list(actions)}}


def scripted_stream(responses: list[dict[str, Any]]):
    """Replace `LitellmModel.query_stream` with a model that returns ``responses`` in order."""
    remaining = list(responses)

    def fake_query_stream(_model, _messages, tools=None, *, on_text, **_kwargs):
        response = remaining.pop(0)
        if response.get("content"):
            on_text(response["content"])
        return {"role": "assistant", **response}

    return patch.object(LitellmModel, "query_stream", new=fake_query_stream)

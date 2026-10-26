"""Characterization tests: the SSE event sequence of one chat turn must stay stable across refactors.

Each test drives `POST /api/chat/stream` with a scripted model and compares the ordered event names
(and key payload fields) for plain replies, tool calls, approval rejection, `O:` corrections,
interruption and the per-turn tool limit.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from tests.chat_helpers import make_chat_repo, parse_sse, reply, scripted_stream, set_permissions
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app


@pytest.fixture
def chat_repo(tmp_path: Path) -> Path:
    return make_chat_repo(tmp_path / "chat_repo")


def _names(events: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [name for name, _data in events]


def _stream(repo: Path, responses: list[dict[str, Any]], **body: Any) -> list[tuple[str, dict[str, Any]]]:
    client = TestClient(create_app(repo_root=repo))
    with scripted_stream(responses):
        response = client.post("/api/chat/stream", json={"thread_id": "th_seq", "model_id": "m1", **body})
    assert response.status_code == 200, response.text
    return parse_sse(response.text)


def test_plain_reply_sequence(chat_repo: Path):
    events = _stream(chat_repo, [reply("Hello there.")], content="hi")
    assert _names(events) == ["thinking", "thinking", "text_chunk", "finish"]
    finish = events[-1][1]
    assert finish["exit_status"] == "finish" and finish["steps"] == 1


def test_tool_call_sequence(chat_repo: Path):
    set_permissions(chat_repo, "allow_all")
    events = _stream(
        chat_repo,
        [reply("Reading.", {"tool_name": "read", "path": "main.py"}), reply("Done.")],
        content="read main.py",
    )
    assert _names(events) == [
        "thinking",
        "thinking",
        "text_chunk",
        "tool_call",
        "tool_result",
        "thinking",
        "text_chunk",
        "finish",
    ]
    assert events[4][1]["returncode"] == 0 and "print('hi')" in events[4][1]["output"]
    assert events[-1][1]["steps"] == 2


async def _stream_with_answer(repo: Path, responses: list[dict[str, Any]], answer: str, **body: Any):
    """Run a turn that pauses for approval, answer it through `/api/chat/confirm` or interrupt."""
    app = create_app(repo_root=repo)
    state = app.state.server_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with scripted_stream(responses):
            task = asyncio.create_task(
                client.post("/api/chat/stream", json={"thread_id": "th_seq", "model_id": "m1", **body})
            )
            for _attempt in range(100):
                if state.pending_approvals:
                    break
                await asyncio.sleep(0.05)
            pending_key = next(iter(state.pending_approvals))
            thread_id, action_id = pending_key.split(":", 1)
            if answer == "interrupt":
                await client.post("/api/chat/interrupt", json={"thread_id": thread_id})
            else:
                confirm = await client.post(
                    "/api/chat/confirm", json={"thread_id": thread_id, "action_id": action_id, "choice": answer}
                )
                assert confirm.status_code == 200
            response = await task
    assert response.status_code == 200
    return parse_sse(response.text)


_APPROVAL_TURN = [reply("Running.", {"command": "echo characterization"}), reply("Finished.")]


@pytest.mark.asyncio
async def test_approved_command_sequence(chat_repo: Path):
    set_permissions(chat_repo, "manual")
    events = await _stream_with_answer(chat_repo, _APPROVAL_TURN, "Y", content="run it")
    names = _names(events)
    assert names[3:6] == ["tool_call", "approval_required", "tool_result"]
    assert events[5][1]["returncode"] == 0 and "characterization" in events[5][1]["output"]
    assert names[-1] == "finish" and events[-1][1]["exit_status"] == "finish"


@pytest.mark.asyncio
async def test_rejected_command_sequence(chat_repo: Path):
    set_permissions(chat_repo, "manual")
    events = await _stream_with_answer(chat_repo, _APPROVAL_TURN, "N", content="run it")
    assert _names(events)[3:6] == ["tool_call", "approval_required", "tool_result"]
    assert events[5][1]["output"].startswith("[Approval Rejected]")
    assert events[-1][1]["exit_status"] == "finish"


@pytest.mark.asyncio
async def test_correction_sequence(chat_repo: Path):
    set_permissions(chat_repo, "manual")
    events = await _stream_with_answer(chat_repo, _APPROVAL_TURN, "O: use dir instead", content="run it")
    assert events[5][1]["output"] == "[User Override/Correction]: use dir instead"
    assert events[-1][1]["exit_status"] == "finish"


@pytest.mark.asyncio
async def test_interrupt_during_approval_sequence(chat_repo: Path):
    set_permissions(chat_repo, "manual")
    events = await _stream_with_answer(chat_repo, _APPROVAL_TURN, "interrupt", content="run it")
    names = _names(events)
    assert names[3:6] == ["tool_call", "approval_required", "tool_result"]
    assert names[-1] == "finish" and events[-1][1]["exit_status"] == "interrupted"
    assert "text_chunk" not in names[6:]


def test_tool_limit_sequence(chat_repo: Path):
    set_permissions(chat_repo, "allow_all")
    models_file = chat_repo / ".agents" / "models_config.json"
    config = json.loads(models_file.read_text(encoding="utf-8"))
    config["models"][0]["max_tool_calls"] = 1
    models_file.write_text(json.dumps(config), encoding="utf-8")
    read_main = {"tool_name": "read", "path": "main.py"}
    events = _stream(chat_repo, [reply("One.", read_main, {"tool_name": "read", "path": "x.py"})], content="go")
    results = [data for name, data in events if name == "tool_result"]
    assert results[1]["output"].startswith("[Tool call limit reached]")
    assert events[-1][1]["exit_status"] == "finish" and events[-1][1]["steps"] == 1


def test_model_error_sequence(chat_repo: Path):
    def failing_stream(_model, _messages, tools=None, *, on_text, **_kwargs):
        raise RuntimeError("provider down")

    client = TestClient(create_app(repo_root=chat_repo))
    with patch.object(LitellmModel, "query_stream", new=failing_stream):
        response = client.post("/api/chat/stream", json={"thread_id": "th_err", "model_id": "m1", "content": "x"})
    events = parse_sse(response.text)
    assert _names(events) == ["thinking", "text_chunk", "finish"]
    assert "provider down" in events[1][1]["content"] and events[-1][1]["exit_status"] == "error"

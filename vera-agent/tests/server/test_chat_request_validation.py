"""Every rejection rule of POST /api/chat/stream request parsing, with the HTTP status it returns."""

import pytest

from vera_agent.server.chat.request import ChatRequestError, parse_chat_request
from vera_agent.server.state import ServerState


@pytest.fixture
def state(tmp_path):
    return ServerState(repo_root=tmp_path)


def _rejects(state, body: dict, status: int, fragment: str) -> None:
    with pytest.raises(ChatRequestError) as caught:
        parse_chat_request(state, body)
    assert caught.value.status_code == status
    assert fragment in caught.value.payload["error"]


def test_minimal_body_gets_a_generated_thread_id_and_defaults(state):
    request = parse_chat_request(state, {"content": "  hello  "})

    assert request.thread_id.startswith("th_") and request.content == "hello"
    assert request.attached_skills == [] and request.images == [] and request.clean_context == []
    assert request.ephemeral is False and request.workflow_context_text == ""


@pytest.mark.parametrize(
    ("body", "status", "fragment"),
    [
        ({"workflow_stage": "bogus"}, 400, "Unsupported workflow stage"),
        ({"workflow_stage": "control_decision"}, 400, "structured workflow_control"),
        (
            {"workflow_stage": "control_decision", "workflow_control": {"type": "other", "condition": "x"}},
            400,
            "supported type",
        ),
        (
            {"workflow_stage": "control_decision", "workflow_control": {"type": "condition", "condition": "  "}},
            400,
            "non-empty condition",
        ),
        (
            {"workflow_stage": "control_decision", "workflow_control": {"type": "loop", "condition": "x"}},
            400,
            "max_iterations",
        ),
        (
            {
                "workflow_stage": "control_decision",
                "workflow_control": {"type": "loop", "condition": "x", "max_iterations": True},
            },
            400,
            "max_iterations",
        ),
        (
            {
                "workflow_stage": "control_decision",
                "workflow_control": {"type": "loop", "condition": "x", "max_iterations": 21},
            },
            400,
            "max_iterations",
        ),
        ({"workflow_control": {"type": "condition", "condition": "x"}}, 400, "only accepted for control_decision"),
        ({"rule_trigger": "delete-everything"}, 400, "Unsupported chat command"),
        ({"attached_skills": "review"}, 400, "attached_skills must be a list"),
        ({"attached_mcps": [""]}, 400, "attached_mcps must be a list"),
        ({"attached_skills": ["not-installed"]}, 409, "not installed"),
        ({"attached_mcps": ["not-configured"]}, 409, "not configured"),
        ({"ephemeral": True, "thread_id": "th_x"}, 400, "side_ prefix"),
        ({"context_messages": "text"}, 400, "at most 100 messages"),
        ({"context_messages": [{"role": "tool", "content": "x"}]}, 400, "user or assistant"),
        ({"context_messages": [{"role": "user", "content": "x" * 30_000}] * 9}, 413, "too large"),
        ({"images": [{"data_url": "data:image/png;base64,AA"}] * 5}, 400, "At most four images"),
        ({"images": [{"data_url": "https://example.com/a.png"}]}, 400, "image data URLs"),
        ({"images": [{"data_url": "data:image/png;base64," + "A" * 11_500_000}]}, 400, "8 MB or smaller"),
    ],
)
def test_invalid_bodies_are_rejected_with_the_documented_status(state, body, status, fragment):
    _rejects(state, body, status, fragment)


@pytest.mark.parametrize(
    ("context", "status", "fragment"),
    [
        ({"task": 5, "upstream": []}, 400, "text task and upstream list"),
        ({"task": "t", "upstream": "x"}, 400, "at most 50 items"),
        ({"task": "t", "upstream": [{"node_id": "a", "title": "t"}]}, 400, "text node_id, title and output"),
        ({"task": "t", "upstream": [{"node_id": "a", "title": "t", "output": "o", "relation": 5}]}, 400, "relation"),
        ({"task": "t", "upstream": [{"node_id": "a", "title": "t", "output": "x" * 100_001}]}, 413, "100000"),
        (
            {"task": "t", "upstream": [{"node_id": str(i), "title": "t", "output": "x" * 90_000} for i in range(3)]},
            413,
            "250000",
        ),
    ],
)
def test_invalid_workflow_context_is_rejected(state, context, status, fragment):
    _rejects(state, {"workflow_context": context}, status, fragment)


def test_valid_workflow_context_is_serialized_with_only_known_fields(state):
    upstream = [{"node_id": "a", "title": "Coder", "output": "done", "relation": "next", "extra": "dropped"}]

    request = parse_chat_request(state, {"workflow_context": {"task": "ship", "upstream": upstream}})

    assert '"task": "ship"' in request.workflow_context_text
    assert '"relation": "next"' in request.workflow_context_text and "dropped" not in request.workflow_context_text


def test_valid_control_decision_and_context_messages_are_accepted(state):
    body = {
        "workflow_stage": "control_decision",
        "workflow_control": {"type": "loop", "condition": "tests pass", "max_iterations": 3},
        "context_messages": [{"role": "user", "content": "x" * 40_000}],
        "ephemeral": True,
        "thread_id": "side_1",
    }

    request = parse_chat_request(state, body)

    assert request.workflow_stage == "control_decision" and request.ephemeral is True
    assert len(request.clean_context[0]["content"]) == 30_000  # each context message is clipped

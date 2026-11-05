"""Chat-completions and Responses API tool-call parsers must accept and reject exactly the same calls."""

import json
from types import SimpleNamespace

import pytest

from vera_agent.exceptions import FormatError
from vera_agent.models.utils.actions_toolcall import parse_toolcall_actions
from vera_agent.models.utils.actions_toolcall_response import parse_toolcall_actions_response

TEMPLATE = "{{ error }}"


def _chat(name: str, arguments: dict | str):
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return parse_toolcall_actions(
        [SimpleNamespace(id="c1", function=SimpleNamespace(name=name, arguments=raw))],
        format_error_template=TEMPLATE,
    )


def _responses(name: str, arguments: dict | str):
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    item = {"type": "function_call", "call_id": "c1", "name": name, "arguments": raw}
    return parse_toolcall_actions_response([{"type": "message"}, item], format_error_template=TEMPLATE)


PARSERS = pytest.mark.parametrize("parse", [_chat, _responses], ids=["chat", "responses"])


@PARSERS
@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        ("bash", {"command": "ls"}, {"command": "ls", "tool_call_id": "c1"}),
        ("bash", {"command": "ls", "timeout": 5}, {"command": "ls", "tool_call_id": "c1", "timeout": 5}),
        ("bash", {"command": "ls", "timeout": None}, {"command": "ls", "tool_call_id": "c1"}),
        (
            "read",
            {"path": "a.py"},
            {"tool_name": "read", "path": "a.py", "offset": 1, "limit": 2000, "command": "read a.py"},
        ),
        ("write", {"path": "a", "content": "x"}, {"tool_name": "write", "path": "a", "content": "x"}),
        (
            "edit",
            {"path": "a", "oldText": "o", "newText": "n"},
            {"tool_name": "edit", "path": "a", "edits": [{"oldText": "o", "newText": "n"}]},
        ),
        ("edit", {"path": "a", "edits": [{"oldText": "o", "newText": "n"}]}, {"tool_name": "edit", "path": "a"}),
        ("delegate_review", {"task": "check"}, {"tool_name": "delegate_review", "task": "check"}),
        ("delegate_research", {"command": "dig"}, {"tool_name": "delegate_research", "task": "dig"}),
    ],
)
def test_valid_calls_become_actions(parse, name, arguments, expected):
    (action,) = parse(name, arguments)

    assert {key: action[key] for key in expected} == expected
    assert action["tool_call_id"] == "c1"


@PARSERS
def test_long_delegation_tasks_are_previewed_in_the_command(parse):
    (action,) = parse("delegate_research", {"task": "x" * 80})

    assert action["command"] == "delegate_research " + "x" * 50 + "..." and action["task"] == "x" * 80


@PARSERS
@pytest.mark.parametrize(
    ("name", "arguments", "fragment"),
    [
        ("bash", {}, "Missing 'command'"),
        ("read", {}, "Missing 'path'"),
        ("write", {"path": "a"}, "Missing 'path' or 'content'"),
        ("edit", {"path": "a"}, "Missing 'path' or 'edits'"),
        ("edit", {"edits": [{"oldText": "o", "newText": "n"}]}, "Missing 'path' or 'edits'"),
        ("delegate_review", {}, "Missing 'task'"),
        ("teleport", {}, "Unknown tool 'teleport'"),
        ("bash", [1, 2], "must be a JSON dictionary"),
        ("bash", "{not json", "Error parsing tool call arguments"),
    ],
)
def test_malformed_calls_raise_a_format_error_naming_the_problem(parse, name, arguments, fragment):
    with pytest.raises(FormatError) as caught:
        parse(name, arguments)

    message = caught.value.messages[0]
    assert fragment in json.dumps(message, ensure_ascii=False)
    assert message["extra"]["interrupt_type"] == "FormatError"


def test_the_chat_parser_accepts_extra_mcp_tools_and_the_responses_parser_does_not_know_them():
    call = SimpleNamespace(id="c9", function=SimpleNamespace(name="mcp__db__query", arguments='{"sql": "select 1"}'))

    actions = parse_toolcall_actions([call], format_error_template=TEMPLATE, additional_tool_names={"mcp__db__query"})

    assert actions == [
        {
            "tool_name": "mcp__db__query",
            "arguments": {"sql": "select 1"},
            "command": "MCP mcp__db__query",
            "tool_call_id": "c9",
        }
    ]


def _empty_reply(parse, **options):
    if parse is _chat:
        return parse_toolcall_actions(None, format_error_template=TEMPLATE, **options)
    return parse_toolcall_actions_response([], format_error_template=TEMPLATE, **options)


@PARSERS
def test_a_reply_without_tool_calls_is_a_format_error(parse):
    with pytest.raises(FormatError) as caught:
        _empty_reply(parse)

    assert "No tool calls found" in json.dumps(caught.value.messages[0])


@PARSERS
def test_a_reply_without_tool_calls_is_fine_when_empty_replies_are_allowed(parse):
    assert _empty_reply(parse, allow_empty=True) == []

"""Orthogonal 4-primitive tools (read, write, edit, bash) unit test suite.

Coverage:
1. read_file_op: read-only checking, line numbering, bounds protection, and pagination.
2. write_file_op: automatic directory creation, atomic full-file write and overwrite.
3. edit_file_op: precise contextual search-and-replace, ambiguous match prevention, sequential multi-edits, and unified diff generation.
4. parse_toolcall_actions & parse_toolcall_actions_response: Function Calling and Responses API dual-format parsing.
"""

from pathlib import Path
from types import SimpleNamespace
import pytest

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions
from minisweagent.models.utils.actions_toolcall_response import parse_toolcall_actions_response
from minisweagent.tools.ops import edit_file_op, read_file_op, write_file_op


# ============================================================================
# 1. read_file_op Primitive Tests
# ============================================================================

def test_read_file_op_success(tmp_path: Path):
    """Test standard file reading with line numbers and formatting."""
    test_file = tmp_path / "sample.py"
    test_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    res = read_file_op("sample.py", base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Showing lines 1-3" in res["output"]
    assert "     1 | line 1" in res["output"]
    assert "     2 | line 2" in res["output"]
    assert "     3 | line 3" in res["output"]


def test_read_file_op_pagination(tmp_path: Path):
    """Test pagination offset and limit parameters."""
    test_file = tmp_path / "long.txt"
    lines = [f"data_{i}" for i in range(1, 11)]
    test_file.write_text("\n".join(lines), encoding="utf-8")

    # Read 3 lines starting from line 4 (lines 4, 5, 6)
    res = read_file_op("long.txt", offset=4, limit=3, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Showing lines 4-6" in res["output"]
    assert "     4 | data_4" in res["output"]
    assert "     6 | data_6" in res["output"]
    assert "truncated" in res["output"]


def test_read_file_op_not_found(tmp_path: Path):
    """Test reading a non-existent file returns error and returncode 1."""
    res = read_file_op("nonexistent.txt", base_dir=tmp_path)
    assert res["returncode"] == 1
    assert "not found" in res["output"]
    assert res["exception_info"] == "FileNotFound"


def test_read_file_op_directory_error(tmp_path: Path):
    """Test reading a directory path returns error without crashing."""
    sub_dir = tmp_path / "sub_dir"
    sub_dir.mkdir()
    res = read_file_op("sub_dir", base_dir=tmp_path)
    assert res["returncode"] == 1
    assert "is a directory" in res["output"]


# ============================================================================
# 2. write_file_op Primitive Tests
# ============================================================================

def test_write_file_op_auto_mkdir(tmp_path: Path):
    """Test writing a new file automatically creates missing parent directories."""
    target = "nested/deep/directory/test.py"
    content = "print('hello world')\n"

    res = write_file_op(target, content, base_dir=tmp_path)
    assert res["returncode"] == 0
    written_file = tmp_path / target
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == content


def test_write_file_op_overwrite(tmp_path: Path):
    """Test overwriting an existing file."""
    target_file = tmp_path / "override.txt"
    target_file.write_text("old content", encoding="utf-8")

    new_content = "new updated content"
    res = write_file_op("override.txt", new_content, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert target_file.read_text(encoding="utf-8") == new_content


# ============================================================================
# 3. edit_file_op Primitive Tests
# ============================================================================

def test_edit_file_op_success(tmp_path: Path):
    """Test precise string matching and replacement with unified diff output."""
    target_file = tmp_path / "calculator.py"
    initial_code = (
        "def add(a, b):\n"
        "    return a - b  # bug here\n"
    )
    target_file.write_text(initial_code, encoding="utf-8")

    edits = [
        {
            "oldText": "    return a - b  # bug here",
            "newText": "    return a + b",
        }
    ]
    res = edit_file_op("calculator.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Successfully applied 1 edit(s)" in res["output"]
    assert "-    return a - b  # bug here" in res["output"]
    assert "+    return a + b" in res["output"]

    # Verify disk file is updated
    updated = target_file.read_text(encoding="utf-8")
    assert "return a + b" in updated
    assert "return a - b" not in updated


def test_edit_file_op_not_found(tmp_path: Path):
    """Test error feedback when old text snippet is not found."""
    target_file = tmp_path / "test.py"
    target_file.write_text("def hello(): pass\n", encoding="utf-8")

    edits = [{"oldText": "def goodbye(): pass", "newText": "pass"}]
    res = edit_file_op("test.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 1
    assert res["exception_info"] == "OldTextNotFound"
    assert "Ensure the target code snippet matches" in res["output"]


def test_edit_file_op_ambiguous_match(tmp_path: Path):
    """Test blocking replacement when multiple occurrences match to prevent unintended edits."""
    target_file = tmp_path / "duplicate.py"
    target_file.write_text("value = 1\n# separator\nvalue = 1\n", encoding="utf-8")

    edits = [{"oldText": "value = 1", "newText": "value = 2"}]
    res = edit_file_op("duplicate.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 1
    assert res["exception_info"] == "AmbiguousOldText"
    assert "matched 2 times" in res["output"]


def test_edit_file_op_multiple_sequential_edits(tmp_path: Path):
    """Test applying multiple non-conflicting edits sequentially in a single invocation."""
    target_file = tmp_path / "multi.py"
    target_file.write_text("x = 10\ny = 20\n", encoding="utf-8")

    edits = [
        {"oldText": "x = 10", "newText": "x = 100"},
        {"oldText": "y = 20", "newText": "y = 200"},
    ]
    res = edit_file_op("multi.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Successfully applied 2 edit(s)" in res["output"]
    assert target_file.read_text(encoding="utf-8") == "x = 100\ny = 200\n"


# ============================================================================
# 4. Parser Tests (Function Calling & Responses API)
# ============================================================================

def test_parse_toolcall_actions_all_primitives():
    """Verify standard OpenAI Function Calling parser for all 4 primitives."""
    # Simulate bash
    bash_call = SimpleNamespace(
        id="call_bash_1",
        function=SimpleNamespace(name="bash", arguments='{"command": "pytest"}'),
    )
    # Simulate read
    read_call = SimpleNamespace(
        id="call_read_1",
        function=SimpleNamespace(name="read", arguments='{"path": "foo.py", "offset": 10}'),
    )
    # Simulate write
    write_call = SimpleNamespace(
        id="call_write_1",
        function=SimpleNamespace(name="write", arguments='{"path": "bar.py", "content": "hello"}'),
    )
    # Simulate edit
    edit_call = SimpleNamespace(
        id="call_edit_1",
        function=SimpleNamespace(name="edit", arguments='{"path": "baz.py", "oldText": "a", "newText": "b"}'),
    )

    actions = parse_toolcall_actions(
        [bash_call, read_call, write_call, edit_call],
        format_error_template="{{ error }}",
    )
    assert len(actions) == 4
    assert actions[0] == {"command": "pytest", "tool_call_id": "call_bash_1"}
    assert actions[1]["tool_name"] == "read"
    assert actions[1]["path"] == "foo.py"
    assert actions[1]["offset"] == 10
    assert actions[1]["command"] == "read foo.py"

    assert actions[2]["tool_name"] == "write"
    assert actions[2]["path"] == "bar.py"
    assert actions[2]["command"] == "write bar.py"

    assert actions[3]["tool_name"] == "edit"
    assert actions[3]["path"] == "baz.py"
    assert actions[3]["edits"] == [{"oldText": "a", "newText": "b"}]
    assert actions[3]["command"] == "edit baz.py"


def test_parse_toolcall_actions_response_all_primitives():
    """Verify OpenAI Responses API flat parser for all 4 primitives."""
    output = [
        {"type": "function_call", "call_id": "call_1", "name": "read", "arguments": '{"path": "test.py"}'},
        {"type": "function_call", "call_id": "call_2", "name": "bash", "arguments": '{"command": "ls -la"}'},
    ]
    actions = parse_toolcall_actions_response(output, format_error_template="{{ error }}")
    assert len(actions) == 2
    assert actions[0]["tool_name"] == "read"
    assert actions[0]["command"] == "read test.py"
    assert actions[1] == {"command": "ls -la", "tool_call_id": "call_2"}


def test_parse_toolcall_unknown_tool_raises_format_error():
    """Verify unknown tool name raises FormatError."""
    bad_call = SimpleNamespace(
        id="bad_1",
        function=SimpleNamespace(name="unknown_tool", arguments='{}'),
    )
    with pytest.raises(FormatError) as exc_info:
        parse_toolcall_actions([bad_call], format_error_template="{{ error }}")
    assert "Unknown tool 'unknown_tool'" in exc_info.value.messages[0]["content"]

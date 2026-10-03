"""Pi-agent 正交 4 基元工具（read, write, edit, bash）单元测试套件。

覆盖范围：
1. read_file_op: 只读检查、行号显示、越界保护与窗口分页。
2. write_file_op: 自动递归建目录、整文件原子写入与覆盖。
3. edit_file_op: 精确上下文查找替换、歧义多处匹配拦截、多块顺序替换及 Unified Diff 生成。
4. parse_toolcall_actions & parse_toolcall_actions_response: Function Calling 与 Responses API 双格式解析。
"""

from pathlib import Path
from types import SimpleNamespace
import pytest

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions
from minisweagent.models.utils.actions_toolcall_response import parse_toolcall_actions_response
from minisweagent.tools.ops import edit_file_op, read_file_op, write_file_op


# ============================================================================
# 1. read_file_op 基元测试
# ============================================================================

def test_read_file_op_success(tmp_path: Path):
    """测试常规文件读取，验证行号与格式。"""
    test_file = tmp_path / "sample.py"
    test_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    res = read_file_op("sample.py", base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Showing lines 1-3" in res["output"]
    assert "     1 | line 1" in res["output"]
    assert "     2 | line 2" in res["output"]
    assert "     3 | line 3" in res["output"]


def test_read_file_op_pagination(tmp_path: Path):
    """测试分页偏移量 (offset) 与限制条数 (limit)。"""
    test_file = tmp_path / "long.txt"
    lines = [f"data_{i}" for i in range(1, 11)]
    test_file.write_text("\n".join(lines), encoding="utf-8")

    # 从第 4 行开始读，读取 3 行 (4, 5, 6)
    res = read_file_op("long.txt", offset=4, limit=3, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert "Showing lines 4-6" in res["output"]
    assert "     4 | data_4" in res["output"]
    assert "     6 | data_6" in res["output"]
    assert "truncated" in res["output"]


def test_read_file_op_not_found(tmp_path: Path):
    """测试读取不存在的文件返回友好错误与 returncode 1。"""
    res = read_file_op("nonexistent.txt", base_dir=tmp_path)
    assert res["returncode"] == 1
    assert "not found" in res["output"]
    assert res["exception_info"] == "FileNotFound"


def test_read_file_op_directory_error(tmp_path: Path):
    """测试读取目录路径时返回错误，避免崩溃。"""
    sub_dir = tmp_path / "sub_dir"
    sub_dir.mkdir()
    res = read_file_op("sub_dir", base_dir=tmp_path)
    assert res["returncode"] == 1
    assert "is a directory" in res["output"]


# ============================================================================
# 2. write_file_op 基元测试
# ============================================================================

def test_write_file_op_auto_mkdir(tmp_path: Path):
    """测试写入新文件并自动创建多级不存在的父目录。"""
    target = "nested/deep/directory/test.py"
    content = "print('hello world')\n"

    res = write_file_op(target, content, base_dir=tmp_path)
    assert res["returncode"] == 0
    written_file = tmp_path / target
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == content


def test_write_file_op_overwrite(tmp_path: Path):
    """测试全量覆盖已存在的文件。"""
    target_file = tmp_path / "override.txt"
    target_file.write_text("old content", encoding="utf-8")

    new_content = "new updated content"
    res = write_file_op("override.txt", new_content, base_dir=tmp_path)
    assert res["returncode"] == 0
    assert target_file.read_text(encoding="utf-8") == new_content


# ============================================================================
# 3. edit_file_op 基元测试
# ============================================================================

def test_edit_file_op_success(tmp_path: Path):
    """测试精准文本查找与替换，并检查返回的 Unified Diff。"""
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

    # 验证磁盘文件内容确实更新
    updated = target_file.read_text(encoding="utf-8")
    assert "return a + b" in updated
    assert "return a - b" not in updated


def test_edit_file_op_not_found(tmp_path: Path):
    """测试旧代码片段不存在时报错并提供友好指导。"""
    target_file = tmp_path / "test.py"
    target_file.write_text("def hello(): pass\n", encoding="utf-8")

    edits = [{"oldText": "def goodbye(): pass", "newText": "pass"}]
    res = edit_file_op("test.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 1
    assert res["exception_info"] == "OldTextNotFound"
    assert "Ensure the target code snippet matches" in res["output"]


def test_edit_file_op_ambiguous_match(tmp_path: Path):
    """测试匹配多处时拦截替换，要求模型提供更多上下文避免误伤。"""
    target_file = tmp_path / "duplicate.py"
    target_file.write_text("value = 1\n# separator\nvalue = 1\n", encoding="utf-8")

    edits = [{"oldText": "value = 1", "newText": "value = 2"}]
    res = edit_file_op("duplicate.py", edits, base_dir=tmp_path)
    assert res["returncode"] == 1
    assert res["exception_info"] == "AmbiguousOldText"
    assert "matched 2 times" in res["output"]


def test_edit_file_op_multiple_sequential_edits(tmp_path: Path):
    """测试单次调用中按序执行多处互不冲突的局部编辑。"""
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
# 4. 解析器测试 (Function Calling & Responses API)
# ============================================================================

def test_parse_toolcall_actions_all_primitives():
    """验证标准 OpenAI Function Calling 格式对 4 基元的解析。"""
    # 模拟 bash
    bash_call = SimpleNamespace(
        id="call_bash_1",
        function=SimpleNamespace(name="bash", arguments='{"command": "pytest"}'),
    )
    # 模拟 read
    read_call = SimpleNamespace(
        id="call_read_1",
        function=SimpleNamespace(name="read", arguments='{"path": "foo.py", "offset": 10}'),
    )
    # 模拟 write
    write_call = SimpleNamespace(
        id="call_write_1",
        function=SimpleNamespace(name="write", arguments='{"path": "bar.py", "content": "hello"}'),
    )
    # 模拟 edit
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
    """验证 OpenAI Responses API 扁平格式对 4 基元的解析。"""
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
    """验证非法工具名称触发 FormatError。"""
    bad_call = SimpleNamespace(
        id="bad_1",
        function=SimpleNamespace(name="unknown_tool", arguments='{}'),
    )
    with pytest.raises(FormatError) as exc_info:
        parse_toolcall_actions([bad_call], format_error_template="{{ error }}")
    assert "Unknown tool 'unknown_tool'" in exc_info.value.messages[0]["content"]

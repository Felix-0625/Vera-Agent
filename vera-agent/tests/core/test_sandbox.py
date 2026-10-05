"""Unit tests for path sandboxing, subagent scratchpad isolation, and multi-turn sanitization."""

import pytest
from pathlib import Path

from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.models.utils.actions_toolcall import parse_toolcall_actions
from vera_agent.tools.ops import (
    edit_file_op,
    read_file_op,
    validate_safe_path,
    write_file_op,
)


def test_validate_safe_path_boundary(tmp_path: Path):
    """Test that escaping workspace boundary with ../ is strictly blocked."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target, err = validate_safe_path("safe.py", base_dir=workspace)
    assert err is None
    assert target == (workspace / "safe.py").resolve()

    # Escape attempt
    target, err = validate_safe_path("../escaped.py", base_dir=workspace)
    assert target is None
    assert err is not None
    assert "AccessDenied" in err


def test_validate_safe_path_subagent_scratch_restriction(tmp_path: Path):
    """Test subagent write restriction: can only write inside allowed scratchpad."""
    workspace = tmp_path / "workspace"
    scratch = workspace / ".agents" / "scratch" / "researcher_123"
    workspace.mkdir()
    scratch.mkdir(parents=True)

    # 1. Read anywhere inside workspace is allowed
    target, err = validate_safe_path(
        "src/payment.py", base_dir=workspace, allowed_write_prefix=scratch, is_write=False
    )
    assert err is None

    # 2. Write inside scratch is allowed
    target, err = validate_safe_path(
        ".agents/scratch/researcher_123/notes.md",
        base_dir=workspace,
        allowed_write_prefix=scratch,
        is_write=True,
    )
    assert err is None

    # 3. Write outside scratch (to project code) is blocked
    target, err = validate_safe_path(
        "src/payment.py", base_dir=workspace, allowed_write_prefix=scratch, is_write=True
    )
    assert target is None
    assert err is not None
    assert "PermissionDenied" in err


def test_ops_subagent_write_blocking(tmp_path: Path):
    """Test that write_file_op and edit_file_op enforce write restriction."""
    workspace = tmp_path / "workspace"
    scratch = workspace / ".agents" / "scratch" / "reviewer_123"
    workspace.mkdir()
    scratch.mkdir(parents=True)

    # Create a project code file
    proj_file = workspace / "core.py"
    proj_file.write_text("x = 1\n", encoding="utf-8")

    # 1. Subagent attempts to write to project code -> BLOCKED
    res_write = write_file_op(
        "core.py", "x = 999\n", base_dir=workspace, allowed_write_prefix=scratch
    )
    assert res_write["returncode"] == 1
    assert res_write["exception_info"] == "PermissionDenied"
    assert proj_file.read_text(encoding="utf-8") == "x = 1\n"

    # 2. Subagent attempts to edit project code -> BLOCKED
    res_edit = edit_file_op(
        "core.py",
        [{"oldText": "x = 1", "newText": "x = 2"}],
        base_dir=workspace,
        allowed_write_prefix=scratch,
    )
    assert res_edit["returncode"] == 1
    assert res_edit["exception_info"] == "PermissionDenied"
    assert proj_file.read_text(encoding="utf-8") == "x = 1\n"

    # 3. Subagent writes to its own scratchpad -> SUCCESS
    res_scratch = write_file_op(
        ".agents/scratch/reviewer_123/audit.md",
        "# Audit Report\nPASS",
        base_dir=workspace,
        allowed_write_prefix=scratch,
    )
    assert res_scratch["returncode"] == 0
    scratch_file = scratch / "audit.md"
    assert scratch_file.exists()
    assert "PASS" in scratch_file.read_text(encoding="utf-8")


def test_local_env_output_truncation(tmp_path: Path):
    """Test that local environment truncates excessively long command/tool outputs."""
    env = LocalEnvironment(
        cwd=str(tmp_path),
        max_output_lines=10,
        max_output_bytes=500,
    )
    # Generate large output
    action = {"tool_name": "bash", "command": "python -c \"print('\\n'.join(str(i) for i in range(100)))\""}
    res = env.execute(action)
    assert res["returncode"] == 0
    assert "Warning: Tool output truncated" in res["output"]
    lines = res["output"].splitlines()
    # Should be limited to around 10 lines + warning
    assert len(lines) <= 15


def test_litellm_model_filters_exit_role():
    """Test that _prepare_messages_for_api strips role == 'exit'."""
    model = LitellmModel(model_name="mock-model", model_kwargs={"drop_params": True})
    raw_msgs = [
        {"role": "system", "content": "sys", "extra": {"foo": "bar"}},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "exit", "content": "Submitted", "extra": {"exit_status": "Submitted"}},
        {"role": "user", "content": "u2"},
    ]
    prepared = model._prepare_messages_for_api(raw_msgs)
    roles = [m["role"] for m in prepared]
    assert "exit" not in roles
    assert roles == ["system", "user", "assistant", "user"]
    # Check extra stripped
    assert all("extra" not in m for m in prepared)


def test_parse_toolcall_actions_allow_empty():
    """Test parse_toolcall_actions with allow_empty=True returns empty list."""
    actions = parse_toolcall_actions(None, format_error_template="{{error}}", allow_empty=True)
    assert actions == []


def test_default_agent_auto_enables_allow_empty_tool_calls(tmp_path: Path):
    """Test that DefaultAgent with complete_on_empty_actions=True auto-enables model.config.allow_empty_tool_calls."""
    from vera_agent.agents.default import DefaultAgent
    model = LitellmModel(model_name="mock-model", model_kwargs={"drop_params": True})
    assert model.config.allow_empty_tool_calls is False

    env = LocalEnvironment(cwd=str(tmp_path))
    agent = DefaultAgent(
        model=model,
        env=env,
        system_template="sys",
        instance_template="inst",
        complete_on_empty_actions=True,
    )
    assert agent.model.config.allow_empty_tool_calls is True

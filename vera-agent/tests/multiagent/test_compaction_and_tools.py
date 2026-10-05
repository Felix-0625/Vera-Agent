"""Unit tests for dynamic role-based tool loading and 3-tier conversation compaction."""

import pytest
from unittest.mock import MagicMock

from minisweagent.session.thread import ThreadSession
from minisweagent.models.litellm_model import LitellmModel, LitellmModelConfig
from minisweagent.models.litellm_response_model import LitellmResponseModel, LitellmResponseModelConfig
from minisweagent.agents.default import DefaultAgent, AgentConfig
from minisweagent.tools import (
    ALL_TOOLS,
    MAIN_AGENT_TOOLS,
    RESEARCHER_TOOLS,
    REVIEWER_TOOLS,
    ALL_TOOLS_RESPONSE_API,
    MAIN_AGENT_TOOLS_RESPONSE_API,
    RESEARCHER_TOOLS_RESPONSE_API,
    REVIEWER_TOOLS_RESPONSE_API,
)


def test_dynamic_tools_for_roles():
    """Verify Pi-agent dynamic tool definitions based on agent role."""
    model = LitellmModel(config_class=LitellmModelConfig, model_name="test-model")
    main_tools = model.get_tools_for_role("main")
    researcher_tools = model.get_tools_for_role("researcher")
    reviewer_tools = model.get_tools_for_role("reviewer")

    # Main agent gets 8 tools (4 primitives + 2 subagent delegation tools + 2 web search & fetch tools)
    assert len(main_tools) == 8
    main_tool_names = {t["function"]["name"] for t in main_tools}
    assert main_tool_names == {
        "read",
        "write",
        "edit",
        "bash",
        "delegate_research",
        "delegate_review",
        "web_search",
        "fetch_web_page",
    }

    # Researcher Subagent gets 6 tools (4 primitives + 2 web tools, strictly NO delegation)
    assert len(researcher_tools) == 6
    researcher_names = {t["function"]["name"] for t in researcher_tools}
    assert researcher_names == {"read", "write", "edit", "bash", "web_search", "fetch_web_page"}
    assert "delegate_research" not in researcher_names
    assert "delegate_review" not in researcher_names

    # Reviewer Subagent gets 4 primitives
    assert len(reviewer_tools) == 4
    reviewer_names = {t["function"]["name"] for t in reviewer_tools}
    assert reviewer_names == {"read", "write", "edit", "bash"}


def test_dynamic_tools_for_response_model():
    """Verify Response API flat schema dynamic tool loading."""
    model = LitellmResponseModel(config_class=LitellmResponseModelConfig, model_name="test-model")
    main_tools = model.get_tools_for_role("main")
    sub_tools = model.get_tools_for_role("researcher")

    assert len(main_tools) == 8
    main_names = {t["name"] for t in main_tools}
    assert main_names == {
        "read",
        "write",
        "edit",
        "bash",
        "delegate_research",
        "delegate_review",
        "web_search",
        "fetch_web_page",
    }

    assert len(sub_tools) == 6
    sub_names = {t["name"] for t in sub_tools}
    assert sub_names == {"read", "write", "edit", "bash", "web_search", "fetch_web_page"}


def test_agent_get_tools_respects_role():
    """Verify DefaultAgent constructs role-specific tool schemas."""
    mock_model = MagicMock()
    mock_model.get_tools_for_role = lambda role: MAIN_AGENT_TOOLS if role == "main" else (RESEARCHER_TOOLS if role == "researcher" else ALL_TOOLS)
    mock_env = MagicMock()
    mock_env.get_template_vars.return_value = {}

    main_agent = DefaultAgent(
        model=mock_model,
        env=mock_env,
        system_template="sys",
        instance_template="inst",
        role="main",
    )
    assert len(main_agent.get_tools()) == 8

    sub_agent = DefaultAgent(
        model=mock_model,
        env=mock_env,
        system_template="sys",
        instance_template="inst",
        role="researcher",
    )
    assert len(sub_agent.get_tools()) == 6
    tool_names = {t["function"]["name"] for t in sub_agent.get_tools()}
    assert "delegate_research" not in tool_names
    assert "web_search" in tool_names


def test_web_search_and_fetch_ops():
    """Verify web search and fetch tools operation."""
    from minisweagent.tools.web_tools import fetch_web_page_op, web_search_op

    # 1. Empty query validation
    empty_res = web_search_op("")
    assert empty_res["returncode"] != 0

    # 2. Real query
    res = web_search_op("python official site", num_results=2)
    assert res["returncode"] == 0
    assert "python" in res["output"].lower()

    # 3. Web fetch test
    fetch_res = fetch_web_page_op("https://httpbin.org/html", max_chars=1000)
    assert fetch_res["returncode"] == 0
    assert "Moby-Dick" in fetch_res["output"]
    assert len(fetch_res["output"]) <= 1500


def test_observation_pruning_level_1():
    """Verify Level 1 Stale Observation Pruning: keeps hot observations, prunes older large observations."""
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Fix bug in foo.py"},
    )

    # Add 6 sequential tool calls with observations
    for i in range(6):
        session.add_messages(
            {
                "role": "assistant",
                "content": f"Step {i}",
                "tool_calls": [{"id": f"call_{i}", "function": {"name": "read", "arguments": '{"path": "foo.py"}'}}],
            },
            {
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "name": "read",
                "content": f"File content of foo.py for step {i}: " + ("x" * 800),
            },
        )

    # We have 2 initial messages + 6 * 2 = 14 messages total.
    # Total observation messages = 6.
    # If keep_last_n_observations=2:
    # Observations 0, 1, 2, 3 should be pruned.
    # Observations 4, 5 (last 2) should remain intact.
    pruned = session.get_chat_history(prune_stale_observations=True, keep_last_n_observations=2, max_observation_chars=200)

    # 1. Total message length should not change
    assert len(pruned) == len(session.messages)

    # 2. Check original session messages are NOT mutated in-place
    assert len(session.messages[3]["content"]) > 800

    # 3. Check observations in pruned history
    tool_msgs = [m for m in pruned if m.get("role") == "tool"]
    assert len(tool_msgs) == 6

    # First 4 should be pruned
    for m in tool_msgs[:4]:
        assert "[Output pruned: read" in m["content"]
        assert len(m["content"]) < 200
        assert m["tool_call_id"].startswith("call_")

    # Last 2 should remain intact
    for m in tool_msgs[4:]:
        assert "[Output pruned" not in m["content"]
        assert len(m["content"]) > 800


def test_boundary_compaction_level_2():
    """Verify Level 2 Boundary Compaction: folds cold turns into structured 4-slot anchor."""
    session = ThreadSession(role="main")
    session.add_messages(
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Implement payment gateway retry logic"},
    )

    # Add 10 dialogue turns
    for i in range(10):
        session.add_messages(
            {
                "role": "assistant",
                "content": f"Step {i} analysis",
                "extra": {"actions": [{"tool_name": "edit", "path": f"module_{i % 3}.py"}]},
            },
            {"role": "user", "content": f"Step {i} observation result"},
        )

    # Total messages: 2 + 20 = 22 messages
    assert len(session.messages) == 22

    # Execute compaction keeping last 4 turns
    success = session.compact(keep_last_n_turns=4)
    assert success is True

    # Expected structure:
    # [0]: system
    # [1]: initial user task
    # [2]: compacted anchor
    # [3:]: last 4 hot turns
    assert len(session.messages) == 2 + 1 + 4
    assert session.messages[0]["role"] == "system"
    assert session.messages[1]["content"] == "Implement payment gateway retry logic"
    assert "<context_compaction>" in session.messages[2]["content"]
    assert "## 1. 原始目标与当前里程碑" in session.messages[2]["content"]
    assert "## 2. 关键架构决策与不可变契约" in session.messages[2]["content"]
    assert "## 3. 已触碰与修改的核心文件" in session.messages[2]["content"]
    assert "## 4. 当前进行中状态与遗留阻碍" in session.messages[2]["content"]
    assert session.messages[2]["extra"]["compaction"] is True


def test_session_rebirth_level_3():
    """Verify Level 3 Epoch Compaction / Session Rebirth."""
    parent = ThreadSession(role="main", cost=1.23, n_calls=15)
    parent.add_messages(
        {"role": "system", "content": "Sys"},
        {"role": "user", "content": "Task 1"},
        {
            "role": "assistant",
            "content": "Phase 1 complete. Created database migration.",
            "extra": {"actions": [{"tool_name": "write", "path": "migrations/001.py"}]},
        },
    )

    child = parent.create_derived_session(new_role="reviewer", extra_notes="Audit migration 001.py")
    assert child.parent_thread_id == parent.thread_id
    assert child.role == "reviewer"
    assert child.metadata["parent_cost"] == 1.23
    assert child.metadata["parent_calls"] == 15
    assert len(child.messages) == 1
    assert f"[INHERITED CONTEXT FROM SESSION {parent.thread_id}]" in child.messages[0]["content"]
    assert "migrations/001.py" in child.messages[0]["content"]
    assert "Audit migration 001.py" in child.messages[0]["content"]

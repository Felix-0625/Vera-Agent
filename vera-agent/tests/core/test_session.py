"""ThreadSession session management layer and context handover test suite.

Coverage:
1. ThreadSession initialization, unique ID generation, and default parameters.
2. Multi-turn message appending, timestamp updates, cost and call count metrics accumulation.
3. get_touched_files extracting read/modified file lists from action history.
4. export_handover_summary generating standardized Markdown context handover documentation.
5. to_dict / from_dict and save / load disk JSON persistence and deserialization.
6. DefaultAgent native ThreadSession binding, state synchronization, and serialization.
"""

from pathlib import Path
import tempfile
import pytest

from minisweagent.agents.default import AgentConfig, DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.test_models import DeterministicModel
from minisweagent.session import ThreadSession


# ============================================================================
# 1. ThreadSession Core Entity Tests
# ============================================================================

def test_thread_session_initialization():
    """Test default initialization properties of the session entity."""
    session = ThreadSession(role="researcher", group_id="grp_core")

    assert session.thread_id.startswith("th_")
    assert session.role == "researcher"
    assert session.group_id == "grp_core"
    assert session.parent_thread_id is None
    assert session.cost == 0.0
    assert session.n_calls == 0
    assert session.messages == []
    assert session.created_at <= session.updated_at


def test_thread_session_messages_and_metrics():
    """Test multi-turn message appending and metric counters accumulation."""
    session = ThreadSession()
    msg1 = {"role": "user", "content": "hello"}
    msg2 = {"role": "assistant", "content": "world"}

    session.add_messages(msg1)
    session.add_messages(msg2)
    assert len(session.messages) == 2
    assert session.messages[0]["content"] == "hello"

    session.add_cost(0.005)
    session.add_cost(0.002)
    session.increment_calls()
    session.increment_calls()

    assert session.cost == pytest.approx(0.007)
    assert session.n_calls == 2


def test_thread_session_get_touched_files():
    """Test extracting touched files from historical actions without duplicates."""
    session = ThreadSession()
    msg = {
        "role": "assistant",
        "content": "I am modifying code",
        "extra": {
            "actions": [
                {"tool_name": "read", "path": "src/utils.py"},
                {"tool_name": "edit", "path": "src/main.py", "edits": []},
                {"tool_name": "read", "path": "src/utils.py"},  # Duplicate read should be deduplicated
            ]
        },
    }
    session.add_messages(msg)

    touched = session.get_touched_files()
    assert len(touched) == 2
    assert touched[0] == {"path": "src/utils.py", "action": "read"}
    assert touched[1] == {"path": "src/main.py", "action": "edit"}


def test_thread_session_export_handover_summary():
    """Test generating a standardized Markdown context handover summary."""
    session = ThreadSession(role="researcher", parent_thread_id="th_main_01")
    session.add_cost(0.015)
    session.increment_calls()

    # Simulate historical actions and final conclusion
    session.add_messages(
        {
            "role": "assistant",
            "content": "Reconnaissance complete: root cause is connection leak in database.py.",
            "extra": {
                "actions": [
                    {"tool_name": "read", "path": "src/db/connection.py"},
                ]
            },
        }
    )

    summary = session.export_handover_summary(
        target_role="coder",
        extra_notes="Please focus on fixing the close_all() logic in connection.py",
    )

    assert "# Context Handover Summary" in summary
    assert f"`{session.thread_id}`" in summary
    assert "**Source Role**: `researcher`" in summary
    assert "**Target Role**: `coder`" in summary
    assert "`th_main_01`" in summary
    assert "`[read]` src/db/connection.py" in summary
    assert "connection leak in database.py" in summary
    assert "Please focus on fixing the close_all() logic" in summary


def test_thread_session_save_and_load(tmp_path: Path):
    """Test persisting session snapshot to JSON and full deserialization."""
    original = ThreadSession(
        role="reviewer",
        group_id="grp_pr_123",
        cost=0.035,
        n_calls=5,
        metadata={"priority": "high"},
    )
    original.add_messages({"role": "user", "content": "review this PR"})

    file_path = tmp_path / "sessions" / f"{original.thread_id}.json"
    saved_path = original.save(file_path)
    assert saved_path.exists()

    restored = ThreadSession.load(saved_path)
    assert restored.thread_id == original.thread_id
    assert restored.role == "reviewer"
    assert restored.group_id == "grp_pr_123"
    assert restored.cost == pytest.approx(0.035)
    assert restored.n_calls == 5
    assert restored.metadata == {"priority": "high"}
    assert len(restored.messages) == 1
    assert restored.messages[0]["content"] == "review this PR"


# ============================================================================
# 2. Agent Integration Tests
# ============================================================================

def test_default_agent_session_binding():
    """Test DefaultAgent automatically attaches and synchronizes ThreadSession."""
    model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "Task completed successfully, core module fixed.",
                "extra": {"cost": 0.002, "actions": []},
            },
        ]
    )
    env = LocalEnvironment()
    agent = DefaultAgent(
        model=model,
        env=env,
        system_template="system",
        instance_template="{{task}}",
        role="coder",
        complete_on_empty_actions=True,
    )

    # Verify initial session binding
    assert isinstance(agent.session, ThreadSession)
    assert agent.session.role == "coder"
    assert agent.messages is agent.session.messages

    # Execute one task
    info = agent.run("Fix the issue")
    assert info["exit_status"] == "Submitted"

    # Verify state synchronized to session entity
    assert agent.session.cost == pytest.approx(0.002)
    assert agent.session.n_calls == 1
    assert len(agent.session.messages) > 0

    # Verify serialized output includes session
    serialized = agent.serialize()
    assert "session" in serialized["info"]
    assert serialized["info"]["session"]["thread_id"] == agent.session.thread_id

    # Verify Agent exports handover summary directly
    handover = agent.export_handover_summary(target_role="reviewer")
    assert "Context Handover Summary" in handover
    assert f"`{agent.session.thread_id}`" in handover

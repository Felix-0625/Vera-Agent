"""ThreadSession 会话管理层与上下文交接接口单元测试套件。

覆盖范围：
1. ThreadSession 初始化、ID 唯一性与默认参数。
2. 消息多轮追加、最近更新时间戳更新、开销与调用计数累加。
3. get_touched_files 从消息动作中精准提取触碰的文件清单。
4. export_handover_summary 生成标准化 Markdown 上下文交接文档。
5. to_dict / from_dict 以及 save / load 磁盘 JSON 持久化与反序列化还原。
6. DefaultAgent / InteractiveAgent 对 ThreadSession 的原生挂载、同步与状态序列化。
"""

from pathlib import Path
import tempfile
import pytest

from minisweagent.agents.default import AgentConfig, DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.test_models import DeterministicModel
from minisweagent.session import ThreadSession


# ============================================================================
# 1. ThreadSession 核心实体测试
# ============================================================================

def test_thread_session_initialization():
    """测试会话实体的默认初始化属性。"""
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
    """测试多轮消息追加与调用度量指标累加。"""
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
    """测试从对话历史动作中自动提取涉及变动的文件列表。"""
    session = ThreadSession()
    msg = {
        "role": "assistant",
        "content": "I am modifying code",
        "extra": {
            "actions": [
                {"tool_name": "read", "path": "src/utils.py"},
                {"tool_name": "edit", "path": "src/main.py", "edits": []},
                {"tool_name": "read", "path": "src/utils.py"},  # 重复读取应去重
            ]
        },
    }
    session.add_messages(msg)

    touched = session.get_touched_files()
    assert len(touched) == 2
    assert touched[0] == {"path": "src/utils.py", "action": "read"}
    assert touched[1] == {"path": "src/main.py", "action": "edit"}


def test_thread_session_export_handover_summary():
    """测试导出标准化上下文交接简报（Markdown）。"""
    session = ThreadSession(role="researcher", parent_thread_id="th_main_01")
    session.add_cost(0.015)
    session.increment_calls()

    # 模拟历史操作与总结答复
    session.add_messages(
        {
            "role": "assistant",
            "content": "已完成架构摸底，发现核心缺陷位于 database.py 连接池未释放。",
            "extra": {
                "actions": [
                    {"tool_name": "read", "path": "src/db/connection.py"},
                ]
            },
        }
    )

    summary = session.export_handover_summary(
        target_role="coder",
        extra_notes="请重点修复 connection.py 中的 close_all() 逻辑",
    )

    assert "# 上下文交接简报 (Handover Summary)" in summary
    assert f"`{session.thread_id}`" in summary
    assert "**发起角色 (Source Role)**: `researcher`" in summary
    assert "**目标角色 (Target Role)**: `coder`" in summary
    assert "`th_main_01`" in summary
    assert "`[read]` src/db/connection.py" in summary
    assert "核心缺陷位于 database.py" in summary
    assert "请重点修复 connection.py" in summary


def test_thread_session_save_and_load(tmp_path: Path):
    """测试会话快照持久化到 JSON 文件并完整反序列化还原。"""
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
# 2. Agent 深度集成测试
# ============================================================================

def test_default_agent_session_binding():
    """测试 DefaultAgent 自动挂载与同步 ThreadSession。"""
    model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "任务已全部搞定，核心模块已修复。",
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

    # 验证初始会话绑定
    assert isinstance(agent.session, ThreadSession)
    assert agent.session.role == "coder"
    assert agent.messages is agent.session.messages

    # 运行一次任务
    info = agent.run("Fix the issue")
    assert info["exit_status"] == "Submitted"

    # 验证状态已同步至 session 实体
    assert agent.session.cost == pytest.approx(0.002)
    assert agent.session.n_calls == 1
    assert len(agent.session.messages) > 0

    # 验证序列化包含 session
    serialized = agent.serialize()
    assert "session" in serialized["info"]
    assert serialized["info"]["session"]["thread_id"] == agent.session.thread_id

    # 验证 Agent 直接导出交接简报
    handover = agent.export_handover_summary(target_role="reviewer")
    assert "上下文交接简报" in handover
    assert f"`{agent.session.thread_id}`" in handover

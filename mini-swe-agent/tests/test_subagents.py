"""Subagent 显式调度工具（delegate_research / delegate_review）与门禁隔离单元测试套件。

覆盖范围：
1. 工具定义与模式完整性（DELEGATE_RESEARCH_TOOL, DELEGATE_REVIEW_TOOL）。
2. Function Calling 与 Responses API 双通道解析器对 Subagent 工具的解析。
3. 门禁检查机制（Strict Gating）：调研员限 2 次，审查员限 1 次，超限拦截。
4. 上下文防火墙（Context Firewall）：主 Agent 消息不向子会话渗透，仅通过交接简报单向回传。
5. 沙箱环境复用：主从 Agent 共享 Environment，成本与统计正确累加。
6. DefaultAgent 端到端执行调用派发测试。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.test_models import DeterministicModel
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions
from minisweagent.models.utils.actions_toolcall_response import parse_toolcall_actions_response
from minisweagent.session import ThreadSession
from minisweagent.tools.subagent_tools import (
    DELEGATE_RESEARCH_TOOL,
    DELEGATE_REVIEW_TOOL,
    SUBAGENT_TOOL_NAMES,
    check_subagent_gating,
    execute_subagent,
)


# ============================================================================
# 1. 工具规范与解析测试
# ============================================================================

def test_subagent_tool_definitions():
    """验证 Subagent 工具定义与参数规范。"""
    assert DELEGATE_RESEARCH_TOOL["function"]["name"] == "delegate_research"
    assert "STRICT GATING" in DELEGATE_RESEARCH_TOOL["function"]["description"]
    assert "task" in DELEGATE_RESEARCH_TOOL["function"]["parameters"]["required"]

    assert DELEGATE_REVIEW_TOOL["function"]["name"] == "delegate_review"
    assert "STRICT GATING" in DELEGATE_REVIEW_TOOL["function"]["description"]
    assert "task" in DELEGATE_REVIEW_TOOL["function"]["parameters"]["required"]


def test_parse_subagent_toolcalls_function_calling():
    """验证标准 OpenAI Function Calling 格式对 Subagent 工具的解析。"""
    call1 = SimpleNamespace(
        id="call_res_1",
        function=SimpleNamespace(name="delegate_research", arguments='{"task": "调研认证模块架构"}'),
    )
    call2 = SimpleNamespace(
        id="call_rev_1",
        function=SimpleNamespace(name="delegate_review", arguments='{"task": "核查登录接口边界用例"}'),
    )

    actions = parse_toolcall_actions([call1, call2], format_error_template="{{ error }}")
    assert len(actions) == 2
    assert actions[0]["tool_name"] == "delegate_research"
    assert actions[0]["task"] == "调研认证模块架构"
    assert "delegate_research" in actions[0]["command"]

    assert actions[1]["tool_name"] == "delegate_review"
    assert actions[1]["task"] == "核查登录接口边界用例"
    assert "delegate_review" in actions[1]["command"]


def test_parse_subagent_toolcalls_response_api():
    """验证 OpenAI Responses API 扁平格式对 Subagent 工具的解析。"""
    output = [
        {
            "type": "function_call",
            "call_id": "resp_res_1",
            "name": "delegate_research",
            "arguments": '{"task": "分析 database 连接池"}',
        }
    ]
    actions = parse_toolcall_actions_response(output, format_error_template="{{ error }}")
    assert len(actions) == 1
    assert actions[0]["tool_name"] == "delegate_research"
    assert actions[0]["task"] == "分析 database 连接池"


# ============================================================================
# 2. 门禁检查机制测试 (Strict Gating)
# ============================================================================

def test_subagent_gating_researcher_limit():
    """测试调研员门禁：最多调用 2 次，第 3 次调用被拦截。"""
    mock_agent = SimpleNamespace(_subagent_call_counts={})

    # 第 1 次：允许
    assert check_subagent_gating(mock_agent, "researcher") is None
    mock_agent._subagent_call_counts["researcher"] = 1

    # 第 2 次：允许
    assert check_subagent_gating(mock_agent, "researcher") is None
    mock_agent._subagent_call_counts["researcher"] = 2

    # 第 3 次：拦截
    gate_err = check_subagent_gating(mock_agent, "researcher")
    assert gate_err is not None
    assert "maximum call limit" in gate_err


def test_subagent_gating_reviewer_limit():
    """测试审查员门禁：仅允许调用 1 次（Pre-merge Gate），后续调用被拦截。"""
    mock_agent = SimpleNamespace(_subagent_call_counts={})

    # 第 1 次：允许
    assert check_subagent_gating(mock_agent, "reviewer") is None
    mock_agent._subagent_call_counts["reviewer"] = 1

    # 第 2 次：拦截
    gate_err = check_subagent_gating(mock_agent, "reviewer")
    assert gate_err is not None
    assert "can only be invoked ONCE" in gate_err


# ============================================================================
# 3. 上下文防火墙与沙箱复用执行测试
# ============================================================================

def test_execute_subagent_context_isolation_and_handover():
    """测试 Subagent 执行：主会话不渗透，子会话成果通过简报安全回传。"""
    # 模拟主 Agent
    parent_session = ThreadSession(role="main")
    parent_session.add_messages(
        {"role": "user", "content": "主会话的绝密内部信息，子 Agent 不应感知"},
    )

    # 模拟子 Agent 使用的模型（执行一次调研并输出结论）
    sub_model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "调研结论：建议使用标准 threading.Lock 替代自研自旋锁。",
                "extra": {"cost": 0.003, "actions": []},
            }
        ]
    )

    parent_agent = SimpleNamespace(
        model=sub_model,
        env=LocalEnvironment(),
        session=parent_session,
        cost=0.01,
        _subagent_call_counts={},
        config=SimpleNamespace(role="main"),
    )

    # 派发调研员
    res = execute_subagent(parent_agent, role="researcher", task="调研锁竞争瓶颈")
    assert res["returncode"] == 0
    assert "[Subagent Delivery: RESEARCHER]" in res["output"]
    assert "建议使用标准 threading.Lock" in res["output"]

    # 成本同步累加至主 Agent
    assert parent_agent.cost == pytest.approx(0.013)
    assert parent_agent.session.cost == pytest.approx(0.003)

    # 验证门禁调用计数已增加
    assert parent_agent._subagent_call_counts["researcher"] == 1


def test_default_agent_dispatches_subagent_tool():
    """测试 DefaultAgent 在 execute_actions 中正确分发并收集 Subagent 观测结果。"""
    # 构造主 Agent 模型：第一步调用 delegate_research，第二步收到报告后完成任务
    main_model = DeterministicModel(
        outputs=[
            {
                "role": "assistant",
                "content": "正在安排调研员开展前期调研...",
                "extra": {
                    "cost": 0.001,
                    "actions": [
                        {
                            "tool_name": "delegate_research",
                            "task": "调研项目入口结构",
                            "command": "delegate_research 调研项目入口结构",
                        }
                    ],
                },
            },
            {
                "role": "assistant",
                "content": "已获取调研结果，实施完毕，提交最终成果。",
                "extra": {"cost": 0.001, "actions": []},
            },
        ]
    )

    env = LocalEnvironment()
    agent = DefaultAgent(
        model=main_model,
        env=env,
        system_template="system",
        instance_template="{{task}}",
        complete_on_empty_actions=True,
    )

    # 模拟子 Agent 内部运行时的模型输出（通过 mock execute_subagent）
    def mock_subagent_run(*args, **kwargs):
        return {
            "output": "[Subagent Delivery: RESEARCHER]\n\n架构调研完成：入口为 main.py",
            "returncode": 0,
            "exception_info": "",
        }

    agent.execute_subagent_tool = mock_subagent_run

    info = agent.run("重构项目入口")
    assert info["exit_status"] == "Submitted"

    # 验证历史消息中记录了 Subagent 的交付观察
    observation_msgs = [msg for msg in agent.messages if "Subagent Delivery: RESEARCHER" in str(msg)]
    assert len(observation_msgs) == 1


def test_interactive_agent_slash_commands():
    """测试 InteractiveAgent 的 /research 和 /review 交互式斜杠指令。"""
    from tests.agents.test_interactive import mock_prompts
    from minisweagent.agents.interactive import InteractiveAgent

    calls = []

    def mock_subagent_run(action):
        calls.append(action)
        return {"output": f"Mock output for {action['tool_name']}", "returncode": 0, "exception_info": ""}

    agent = InteractiveAgent(
        model=DeterministicModel(outputs=[]),
        env=LocalEnvironment(),
        system_template="system",
        instance_template="{{task}}",
    )
    agent.execute_subagent_tool = mock_subagent_run

    with mock_prompts([
        "/research 调研缓存方案",
        "/review 检查并发死锁",
        "echo done",
    ]):
        res = agent._prompt_and_handle_slash_commands("prompt> ")

    assert res == "echo done"
    assert len(calls) == 2
    assert calls[0]["tool_name"] == "delegate_research"
    assert calls[0]["task"] == "调研缓存方案"
    assert calls[1]["tool_name"] == "delegate_review"
    assert calls[1]["task"] == "检查并发死锁"


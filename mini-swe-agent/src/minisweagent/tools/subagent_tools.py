"""Subagent 显式重武器调度工具（delegate_research / delegate_review）与门禁执行器。

严格遵循微观黄金三角协作哲学：
1. 显式调用（Explicit Invocation）：主 Agent 工具集显式暴露，严禁黑盒后台自循环。
2. 严苛门禁（Strict Gating）：调研员限 2 次复杂架构探索；审查员限 1 次交付前最终审核。
3. 上下文防火墙（Context Firewall）：主从 Agent 会话隔离，仅回传提炼后的交接简报。
4. 沙箱复用：主从 Agent 共享同一个 Environment 实例。
"""

from __future__ import annotations

import logging
from typing import Any

from minisweagent.config import get_config_from_spec
from minisweagent.session import ThreadSession

logger = logging.getLogger("subagent_tools")

# ============================================================================
# 1. OpenAI Function Calling 规范
# ============================================================================

DELEGATE_RESEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "delegate_research",
        "description": (
            "Delegate complex codebase reconnaissance and architecture investigation to the read-only Researcher subagent. "
            "STRICT GATING: Only call when exploring 5+ unfamiliar files, complex cross-module dependencies, or evaluating a new technology stack. "
            "PROHIBITED for single-file lookups, simple questions, or known bug locations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Specific research objective, scope, and technical questions to investigate in the codebase.",
                },
            },
            "required": ["task"],
        },
    },
}

DELEGATE_REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "delegate_review",
        "description": (
            "Delegate pre-merge code review and adversarial quality audit to the Reviewer subagent. "
            "STRICT GATING: Only call ONCE as the final quality gate after all implementations are complete and self-smoke tests pass. "
            "PROHIBITED during mid-implementation or before self-testing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Verification scope, modified files to audit, and specific edge cases to test.",
                },
            },
            "required": ["task"],
        },
    },
}

# ============================================================================
# 2. OpenAI Responses API 扁平规范
# ============================================================================

DELEGATE_RESEARCH_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "delegate_research",
    "description": DELEGATE_RESEARCH_TOOL["function"]["description"],
    "parameters": DELEGATE_RESEARCH_TOOL["function"]["parameters"],
}

DELEGATE_REVIEW_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "delegate_review",
    "description": DELEGATE_REVIEW_TOOL["function"]["description"],
    "parameters": DELEGATE_REVIEW_TOOL["function"]["parameters"],
}

SUBAGENT_TOOLS = [DELEGATE_RESEARCH_TOOL, DELEGATE_REVIEW_TOOL]
SUBAGENT_TOOLS_RESPONSE_API = [DELEGATE_RESEARCH_TOOL_RESPONSE_API, DELEGATE_REVIEW_TOOL_RESPONSE_API]
SUBAGENT_TOOL_NAMES = {"delegate_research", "delegate_review"}


# ============================================================================
# 3. 门禁检查与执行引擎 (Gatekeeper & Executor)
# ============================================================================

# 单次主任务会话内允许调用的最大次数约束
MAX_SUBAGENT_CALLS = {
    "researcher": 2,
    "reviewer": 1,
}


def check_subagent_gating(parent_agent: Any, role: str) -> str | None:
    """检查 Subagent 调用门禁。若违规返回拦截原因，合规返回 None。"""
    counts = getattr(parent_agent, "_subagent_call_counts", None)
    if counts is None:
        parent_agent._subagent_call_counts = {}
        counts = parent_agent._subagent_call_counts

    current_calls = counts.get(role, 0)
    max_allowed = MAX_SUBAGENT_CALLS.get(role, 1)

    if current_calls >= max_allowed:
        if role == "reviewer":
            return (
                "Gating Blocked: Reviewer subagent can only be invoked ONCE as the final Pre-merge Gate. "
                "You have already performed the final review. Please proceed to submit your work."
            )
        elif role == "researcher":
            return (
                f"Gating Blocked: Researcher subagent maximum call limit ({max_allowed}) reached for this session. "
                "Please synthesize existing findings and proceed with implementation directly."
            )
        else:
            return f"Gating Blocked: Subagent '{role}' call limit ({max_allowed}) reached."

    return None


def execute_subagent(
    parent_agent: Any,
    role: str,
    task: str,
    *,
    config_spec: str | None = None,
) -> dict[str, Any]:
    """在共享沙箱环境中安全派发并执行子 Agent。

    - 门禁校验：严格拦截超额调用，避免死循环；
    - 上下文隔离：构建专属子会话，主会话历史不向子 Agent 泄露；
    - 成本与统计：子 Agent 消耗实时回传累加至主会话；
    - 简报交接：输出标准化 Markdown 交接内容，充当上下文防火墙。
    """
    # 1. 门禁前置拦截
    gate_error = check_subagent_gating(parent_agent, role)
    if gate_error:
        logger.warning(f"Subagent '{role}' gated: {gate_error}")
        return {
            "output": f"Error: {gate_error}",
            "returncode": 1,
            "exception_info": "SubagentGatingBlocked",
        }

    # 累加调用次数
    parent_agent._subagent_call_counts[role] = parent_agent._subagent_call_counts.get(role, 0) + 1

    # 2. 加载子 Agent 配置
    cfg_name = config_spec or f"subagents/{role}.yaml"
    try:
        sub_config_dict = get_config_from_spec(cfg_name)
    except Exception as e:
        logger.error(f"Failed to load subagent config for '{role}' from '{cfg_name}': {e}")
        return {
            "output": f"Error: Failed to load config for subagent '{role}': {e}",
            "returncode": 1,
            "exception_info": "ConfigLoadError",
        }

    # 3. 构造子会话（挂载父级 thread_id）
    parent_session_id = parent_agent.session.thread_id if hasattr(parent_agent, "session") else None
    sub_session = ThreadSession(
        role=role,
        parent_thread_id=parent_session_id,
        metadata={"delegated_task": task, "config": sub_config_dict.get("agent", {})},
    )

    # 4. 实例化子 Agent（共享模型与执行环境，上下文彻底隔离）
    from minisweagent.agents.default import DefaultAgent

    agent_kwargs = dict(sub_config_dict.get("agent", {}))
    agent_kwargs["session"] = sub_session
    # 强制子 Agent 在无动作输出时自动交付
    agent_kwargs["complete_on_empty_actions"] = True

    try:
        sub_agent = DefaultAgent(
            model=parent_agent.model,
            env=parent_agent.env,
            **agent_kwargs,
        )
        logger.info(f"Dispatching subagent '{role}' with task: {task[:60]}...")
        info = sub_agent.run(task)
    except Exception as e:
        logger.error(f"Subagent '{role}' execution failed: {e}")
        return {
            "output": f"Error running subagent '{role}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }

    # 5. 成本与调用计数同步至主 Agent
    if hasattr(parent_agent, "cost"):
        parent_agent.cost += sub_agent.cost
    if hasattr(parent_agent, "session"):
        parent_agent.session.add_cost(sub_agent.cost)

    # 6. 生成标准交付简报 (Handover Summary)
    handover_report = sub_agent.export_handover_summary(
        target_role=getattr(parent_agent.config, "role", "main"),
        extra_notes=f"Subagent execution exit status: {info.get('exit_status', 'Unknown')}",
    )

    output = f"[Subagent Delivery: {role.upper()}]\n\n{handover_report}"
    return {"output": output, "returncode": 0, "exception_info": ""}

"""Subagent explicit delegation tools (delegate_research / delegate_review) and gating executor.

Follows the core multi-agent coordination principles:
1. Explicit Invocation: Explicitly exposed in the main agent's toolset; no uncontrolled hidden loops.
2. Strict Gating: Researcher is limited to 2 exploratory calls; Reviewer is limited to 1 final pre-merge audit.
3. Context Firewall: Complete conversation isolation between parent and child agents; returns only a refined Handover Summary.
4. Sandbox Reuse: Parent and child agents share the same runtime Environment instance.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

from vera_agent.config import get_config_from_spec
from vera_agent.session import ThreadSession

logger = logging.getLogger("subagent_tools")

# ============================================================================
# 1. OpenAI Function Calling Schema
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
# 2. OpenAI Responses API Flat Schema
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
# 3. Gatekeeper and Execution Engine
# ============================================================================

# Maximum permitted invocation limits per main session
MAX_SUBAGENT_CALLS = {
    "researcher": 2,
    "reviewer": 1,
}


def check_subagent_gating(parent_agent: Any, role: str) -> str | None:
    """Check gating limits for subagent invocation. Returns error reason if blocked, else None."""
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
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Safely dispatch and execute a subagent within the shared environment.

    - Gating Validation: Blocks excess invocations to prevent infinite loops.
    - Context Firewall: Spawns dedicated child session; parent history is not leaked to subagent.
    - Metrics Aggregation: Subagent cost and calls are synchronized back to the parent session.
    - Handover Delivery: Generates standardized Markdown summary as the sole cross-session observation.
    """
    # 1. Pre-execution gating check
    gate_error = check_subagent_gating(parent_agent, role)
    if gate_error:
        logger.warning(f"Subagent '{role}' gated: {gate_error}")
        return {
            "output": f"Error: {gate_error}",
            "returncode": 1,
            "exception_info": "SubagentGatingBlocked",
        }

    # Increment invocation count
    parent_agent._subagent_call_counts[role] = parent_agent._subagent_call_counts.get(role, 0) + 1

    # 2. Load subagent configuration
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

    # 3. Construct child session (linking parent thread_id)
    parent_session_id = parent_agent.session.thread_id if hasattr(parent_agent, "session") else None
    sub_session = ThreadSession(
        role=role,
        parent_thread_id=parent_session_id,
        metadata={"delegated_task": task, "config": sub_config_dict.get("agent", {})},
    )
    run: dict[str, Any] = {
        "id": sub_session.thread_id,
        "title": "研究员" if role == "researcher" else "审查员",
        "role": role,
        "task": task,
        "status": "running",
        "activities": [],
        "result": "",
        "started_at": time.time(),
    }

    def publish(event: dict[str, Any] | None = None) -> None:
        if not on_progress:
            return
        if event:
            if event.get("kind") == "result":
                run["result"] = str(event.get("content", ""))
            else:
                run["activities"] = [*run["activities"], {
                    "label": str(event.get("label", "正在执行")),
                    "detail": str(event.get("detail", "")),
                    "status": str(event.get("status", "working")),
                    "timestamp": time.time(),
                }]
        on_progress(dict(run, activities=list(run["activities"])))

    publish({"kind": "status", "label": "启动子智能体", "detail": "正在准备隔离会话"})

    # 4. Give every child its own writable area. Reads are rooted at the project,
    # while write/edit tools are confined to the child's generated directory.
    from vera_agent.agents.default import DefaultAgent
    from vera_agent.environments.local import LocalEnvironment

    parent_workspace = Path(getattr(parent_agent.env.config, "cwd", os.getcwd())).resolve()
    work_parent = (parent_workspace / ".agents" / "subagents").resolve()
    if not work_parent.is_relative_to(parent_workspace):
        return {"output": "Error: Subagent workspace path escaped the project root.", "returncode": 1, "exception_info": "WorkspaceBoundaryError"}
    work_parent.mkdir(parents=True, exist_ok=True)
    work_area = work_parent / sub_session.thread_id
    work_area.mkdir(parents=True, exist_ok=False)
    simple_readme_check = role == "researcher" and bool(re.search(r"\breadme(?:\.md)?\b|自述文件", task, re.IGNORECASE)) and not any(
        marker in task.lower() for marker in ("多个文件", "全项目", "架构", "调用链", "深入", "对比", "评估", "many files", "architecture")
    )
    read_only_env = None
    if isinstance(parent_agent.env, LocalEnvironment):
        local_env = LocalEnvironment(
            cwd=str(parent_workspace),
            timeout=getattr(parent_agent.env.config, "timeout", 30),
            env=dict(getattr(parent_agent.env.config, "env", {})),
            allowed_write_prefix=str(work_area),
            allow_external_read=bool(getattr(parent_agent.env.config, "allow_external_read", False)),
        )
        class SubagentWorkspaceEnvironment:
            """Apply the parent's action whitelist and isolate child write tools."""
            def __init__(self, inner, root: Path, workspace: Path, parent):
                self._inner = inner
                self._root = root
                self._workspace = workspace
                self.config = inner.config
                self.parent = parent
                self.after_read = None

            def execute(self, action: dict, *args, **kwargs):
                from vera_agent.server.permissions import permission_category, record_tool_result, reserve_tool_call, requires_approval

                tool_name = str(action.get("tool_name") or ("bash" if "command" in action else ""))
                parent_session = getattr(self.parent, "session", None)
                parent_metadata = getattr(parent_session, "metadata", {})
                group_tools = parent_metadata.get("allowed_tools") if isinstance(parent_metadata, dict) else None
                if getattr(parent_session, "group_id", None) and isinstance(group_tools, list) and tool_name not in group_tools:
                    return {"output": f"This subagent action is not allowed for the parent group role ({tool_name or 'unknown'}).", "returncode": 1, "exception_info": "GroupToolDenied"}

                category = permission_category(action, str(self._root))
                mode = getattr(self.parent, "permission_mode", "manual")
                approval_actions = getattr(self.parent, "permission_approval_actions", [])
                if requires_approval(mode, category, action, approval_actions):
                    return {"output": f"This subagent action requires approval in the main conversation ({category}); run it from the main agent instead.", "returncode": 1, "exception_info": "GlobalPermissionDenied"}
                budget = getattr(self.parent, "tool_call_budget", None)
                call_key = None
                if isinstance(budget, dict):
                    call_key, budget_error = reserve_tool_call(budget, action)
                    if budget_error:
                        return {"output": budget_error, "returncode": 1, "exception_info": "ToolCallLimitExceeded" if budget_error.startswith("[Tool call limit") else "ToolAttemptLimitExceeded"}
                if tool_name == "bash":
                    result = self._inner.execute(action, cwd=str(self._workspace), *args, **kwargs)
                else:
                    result = self._inner.execute(action, *args, **kwargs)
                if isinstance(budget, dict) and call_key is not None:
                    record_tool_result(budget, call_key, result)
                if tool_name == "read" and result.get("returncode", 0) == 0 and self.after_read:
                    self.after_read()
                return result

            def __getattr__(self, name):
                return getattr(self._inner, name)

        read_only_env = SubagentWorkspaceEnvironment(local_env, parent_workspace, work_area, parent_agent)
        sub_env = read_only_env
    else:
        sub_env = parent_agent.env

    agent_kwargs = dict(sub_config_dict.get("agent", {}))
    if simple_readme_check:
        agent_kwargs["system_template"] += (
            "\n\nThis is a narrow, single-file README check. Read README.md once, then answer from that result. "
            "Do not inspect other files, use web search, or create any report."
        )
    agent_kwargs["session"] = sub_session
    # Ensure subagent finishes when no further actions are generated
    agent_kwargs["complete_on_empty_actions"] = True

    try:
        sub_agent = DefaultAgent(
            model=parent_agent.model,
            env=sub_env,
            **agent_kwargs,
        )
        sub_agent.permission_mode = getattr(parent_agent, "permission_mode", "manual")
        sub_agent.permission_approval_actions = getattr(parent_agent, "permission_approval_actions", [])
        execute_web_tool = sub_agent.execute_web_tool

        def guarded_web_tool(action: dict) -> dict[str, Any]:
            from vera_agent.server.permissions import permission_category, record_tool_result, reserve_tool_call, requires_approval

            parent_session = getattr(parent_agent, "session", None)
            parent_metadata = getattr(parent_session, "metadata", {})
            group_tools = parent_metadata.get("allowed_tools") if isinstance(parent_metadata, dict) else None
            tool_name = str(action.get("tool_name") or "")
            if getattr(parent_session, "group_id", None) and isinstance(group_tools, list) and tool_name not in group_tools:
                return {"output": f"This subagent action is not allowed for the parent group role ({tool_name or 'unknown'}).", "returncode": 1, "exception_info": "GroupToolDenied"}

            category = permission_category(action, str(parent_workspace))
            if requires_approval(sub_agent.permission_mode, category, action, sub_agent.permission_approval_actions):
                return {"output": f"This subagent action requires approval in the main conversation ({category}); run it from the main agent instead.", "returncode": 1, "exception_info": "GlobalPermissionDenied"}
            budget = getattr(parent_agent, "tool_call_budget", None)
            call_key = None
            if isinstance(budget, dict):
                call_key, budget_error = reserve_tool_call(budget, action)
                if budget_error:
                    return {"output": budget_error, "returncode": 1, "exception_info": "ToolCallLimitExceeded" if budget_error.startswith("[Tool call limit") else "ToolAttemptLimitExceeded"}
            result = execute_web_tool(action)
            if isinstance(budget, dict) and call_key is not None:
                record_tool_result(budget, call_key, result)
            return result

        sub_agent.execute_web_tool = guarded_web_tool
        if simple_readme_check and read_only_env:
            sub_agent._tools_disabled = False
            read_only_env.after_read = lambda: setattr(sub_agent, "_tools_disabled", True)
        sub_agent.progress_callback = publish
        logger.info(f"Dispatching subagent '{role}' with task: {task[:60]}...")
        info = sub_agent.run(task)
    except Exception as e:
        logger.error(f"Subagent '{role}' execution failed: {e}")
        run["status"] = "failed"
        run["result"] = f"子智能体执行失败：{e}"
        run["finished_at"] = time.time()
        publish()
        return {
            "output": f"Error running subagent '{role}': {e}",
            "returncode": 1,
            "exception_info": str(e),
            "subagent": run,
        }

    # 5. Synchronize cost and call counts back to parent agent
    if hasattr(parent_agent, "cost"):
        parent_agent.cost += sub_agent.cost
    if hasattr(parent_agent, "session"):
        parent_agent.session.add_cost(sub_agent.cost)

    # 6. Generate standardized handover summary
    extra_notes = f"Subagent execution exit status: {info.get('exit_status', 'Unknown')}"

    handover_report = sub_agent.export_handover_summary(
        target_role=getattr(parent_agent.config, "role", "main"),
        extra_notes=extra_notes,
    )

    output = f"[Subagent Delivery: {role.upper()}]\n\n{handover_report}"
    run["status"] = "completed" if info.get("exit_status") == "Submitted" else "failed"
    run["result"] = sub_session.get_last_assistant_text() or run["result"] or handover_report
    run["finished_at"] = time.time()
    run["activities"] = [
        dict(activity, status="done" if activity.get("status") == "working" else activity.get("status"))
        for activity in run["activities"]
    ]
    publish()
    return {"output": output, "returncode": 0 if run["status"] == "completed" else 1, "exception_info": "", "subagent": run}

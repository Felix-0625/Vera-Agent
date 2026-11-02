"""Workspace, progress and web-tool adapters used during explicit delegation."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from vera_agent.tools.subagent_environment import SubagentWorkspaceEnvironment


def create_subagent_workspace(parent_agent: Any, role: str, task: str, sub_session):
    # LocalEnvironment imports the tool registry; defer this import until dispatch.
    from vera_agent.environments.local import LocalEnvironment

    parent_workspace = Path(getattr(parent_agent.env.config, "cwd", os.getcwd())).resolve()
    work_parent = (parent_workspace / ".agents" / "subagents").resolve()
    if not work_parent.is_relative_to(parent_workspace):
        return {
            "output": "Error: Subagent workspace path escaped the project root.",
            "returncode": 1,
            "exception_info": "WorkspaceBoundaryError",
        }
    work_parent.mkdir(parents=True, exist_ok=True)
    work_area = work_parent / sub_session.thread_id
    work_area.mkdir(parents=True, exist_ok=False)
    simple_readme_check = (
        role == "researcher"
        and bool(re.search(r"\breadme(?:\.md)?\b|自述文件", task, re.IGNORECASE))
        and not any(
            marker in task.lower()
            for marker in ("多个文件", "全项目", "架构", "调用链", "深入", "对比", "评估", "many files", "architecture")
        )
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

        read_only_env = SubagentWorkspaceEnvironment(local_env, parent_workspace, work_area, parent_agent)
        sub_env = read_only_env
    else:
        sub_env = parent_agent.env

    return parent_workspace, sub_env, read_only_env, simple_readme_check


def make_progress_publisher(run: dict, on_progress):
    def publish(event: dict[str, Any] | None = None) -> None:
        if not on_progress:
            return
        if event:
            if event.get("kind") == "result":
                run["result"] = str(event.get("content", ""))
            else:
                run["activities"] = [
                    *run["activities"],
                    {
                        "label": str(event.get("label", "正在执行")),
                        "detail": str(event.get("detail", "")),
                        "status": str(event.get("status", "working")),
                        "timestamp": time.time(),
                    },
                ]
        on_progress(dict(run, activities=list(run["activities"])))

    return publish


def make_guarded_web_tool(parent_agent: Any, parent_workspace: Path, sub_agent: Any, execute_web_tool):
    def guarded_web_tool(action: dict) -> dict[str, Any]:
        from vera_agent.server.permissions import (
            permission_category,
            record_tool_result,
            requires_approval,
            reserve_tool_call,
        )

        parent_session = getattr(parent_agent, "session", None)
        parent_metadata = getattr(parent_session, "metadata", {})
        group_tools = parent_metadata.get("allowed_tools") if isinstance(parent_metadata, dict) else None
        tool_name = str(action.get("tool_name") or "")
        if getattr(parent_session, "group_id", None) and isinstance(group_tools, list) and tool_name not in group_tools:
            return {
                "output": f"This subagent action is not allowed for the parent group role ({tool_name or 'unknown'}).",
                "returncode": 1,
                "exception_info": "GroupToolDenied",
            }

        category = permission_category(action, str(parent_workspace))
        if requires_approval(sub_agent.permission_mode, category, action, sub_agent.permission_approval_actions):
            return {
                "output": f"This subagent action requires approval in the main conversation ({category}); run it from the main agent instead.",
                "returncode": 1,
                "exception_info": "GlobalPermissionDenied",
            }
        budget = getattr(parent_agent, "tool_call_budget", None)
        call_key = None
        if isinstance(budget, dict):
            call_key, budget_error = reserve_tool_call(budget, action)
            if budget_error:
                return {
                    "output": budget_error,
                    "returncode": 1,
                    "exception_info": "ToolCallLimitExceeded"
                    if budget_error.startswith("[Tool call limit")
                    else "ToolAttemptLimitExceeded",
                }
        result = execute_web_tool(action)
        if isinstance(budget, dict) and call_key is not None:
            record_tool_result(budget, call_key, result)
        return result

    return guarded_web_tool


def complete_subagent(parent_agent, sub_agent, sub_session, info: dict, run: dict, publish, role: str) -> dict:
    """Aggregate costs and deliver the isolated child result to its parent."""
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
    return {
        "output": output,
        "returncode": 0 if run["status"] == "completed" else 1,
        "exception_info": "",
        "subagent": run,
    }

"""Execute the tool actions returned by one model step and stream their SSE events.

For each action: enforce the tool budget, the group role's allowed tools, and the permission
policy (asking the injected `ApprovalPolicy` and emitting `approval_required` when needed), then
run it: user memory, subagent delegation, web tools, MCP tools, or the local environment (files
and shell). An optional `TurnTracer` records one tool span per action with its approval result.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from vera_agent.server.chat.subagents import relay_subagent
from vera_agent.server.permissions import (
    permission_category,
    record_tool_result,
    requires_approval,
    reserve_tool_call,
)
from vera_agent.server.user_context import (
    delete_user_memory,
    upsert_user_memory,
)

logger = logging.getLogger("vera_server.chat")


@dataclass
class ActionBatchResult:
    """Outputs for the model's observation message, and whether the turn's tool budget ran out."""

    outputs: list[dict] = field(default_factory=list)
    tool_limit_reached: bool = False


_TOOL_LABELS = {
    "read": "读取文件",
    "write": "写入文件",
    "edit": "修改文件",
    "web_search": "网页搜索",
    "fetch_web_page": "读取网页",
    "delegate_research": "研究任务",
    "delegate_review": "审查任务",
    "remember_user": "沉淀用户记忆",
    "forget_user_memory": "删除用户记忆",
}
_MEMORY_TOOLS = {"remember_user", "forget_user_memory"}


def tool_result_event(action_id: str, tool_name: str, output: str, returncode: int) -> str:
    payload = {"action_id": action_id, "tool_name": tool_name, "output": output, "returncode": returncode}
    return f"event: tool_result\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def approval_required_event(action_id: str, tool_name: str, action: dict, message: str) -> str:
    payload = {"action_id": action_id, "tool_name": tool_name, "args": action, "message": message}
    return f"event: approval_required\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def group_denied_output(tool_name: str) -> dict:
    return {
        "output": f"[Group role denied] Tool '{tool_name or 'unknown'}' is not allowed for this conversation window.",
        "returncode": 1,
        "exception_info": "GroupToolDenied",
    }


def _budget_rejection(budget_error: str, result: ActionBatchResult) -> tuple[dict, str]:
    exception_info = (
        "ToolCallLimitExceeded" if budget_error.startswith("[Tool call limit") else "ToolAttemptLimitExceeded"
    )
    result.tool_limit_reached = exception_info == "ToolCallLimitExceeded"
    detail = "已达到本轮工具调用上限" if result.tool_limit_reached else "已达到该操作的失败重试上限"
    return {"output": budget_error, "returncode": 1, "exception_info": exception_info}, detail


def _approval_rejection(choice: str) -> tuple[dict, str, str] | None:
    """Map a non-approving choice to (output, activity status, activity detail); None when approved."""
    if choice.upper().startswith("N"):
        output = {
            "output": "[Approval Rejected] Operation rejected by user.",
            "returncode": 1,
            "exception_info": "Approval Rejected",
        }
        return output, "error", "用户拒绝"
    if choice.upper().startswith("O:"):
        output = {"output": f"[User Override/Correction]: {choice[2:].strip()}", "returncode": 1, "exception_info": ""}
        return output, "done", "已提交修改意见"
    return None


def _render_mcp_result(mcp_result: Any) -> dict:
    rendered = []
    for item in mcp_result.content:
        if getattr(item, "text", None) is not None:
            rendered.append(item.text)
        else:
            rendered.append(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
    return {
        "output": "\n".join(rendered)[:5000],
        "returncode": 1 if mcp_result.isError else 0,
        "exception_info": "MCP tool returned an error" if mcp_result.isError else "",
    }


def _run_memory_tool(state, thread_id: str, tool_name: str, act: dict) -> dict:
    arguments = act.get("arguments", {})
    if tool_name == "remember_user":
        memory = upsert_user_memory(
            state,
            str(arguments.get("category", "")),
            str(arguments.get("content", "")),
            memory_id=str(arguments["memory_id"]) if arguments.get("memory_id") else None,
            source_thread_id=thread_id,
            require_existing=bool(arguments.get("memory_id")),
        )
        return {"output": f"已保存用户记忆：{memory['content']}", "returncode": 0, "extra": {"memory_id": memory["id"]}}
    memory_id = str(arguments.get("memory_id", ""))
    deleted = bool(memory_id) and delete_user_memory(state, memory_id)
    return {
        "output": "已删除指定的用户记忆。" if deleted else "没有找到对应的用户记忆。",
        "returncode": 0 if deleted else 1,
    }


async def _execute_action(
    act: dict, tool_name: str, holder: dict, *, state, agent, env, thread_id, mcp_dispatch, subagent_runs
):
    """Run one approved action, yielding subagent progress events; stores the output in ``holder``."""
    try:
        if tool_name in _MEMORY_TOOLS:
            out = _run_memory_tool(state, thread_id, tool_name, act)
        elif tool_name in {"delegate_research", "delegate_review"}:
            relay_result: dict[str, Any] = {}
            async for subagent_event in relay_subagent(agent.execute_subagent_tool, act, subagent_runs, relay_result):
                yield subagent_event
            out = relay_result["output"]
        elif tool_name in {"web_search", "fetch_web_page"}:
            out = await asyncio.to_thread(agent.execute_web_tool, act)
        elif tool_name in mcp_dispatch:
            mcp_session, remote_tool_name = mcp_dispatch[tool_name]
            out = _render_mcp_result(await mcp_session.call_tool(remote_tool_name, arguments=act.get("arguments", {})))
        else:
            # Keep the ASGI loop responsive so pause/interrupt and other conversation
            # controls remain actionable while a synchronous environment tool is running.
            out = await asyncio.to_thread(env.execute, act)
        out.setdefault("exception_info", "")
    except Exception as error:
        out = {"output": f"Execution error: {error}", "returncode": -1, "exception_info": str(error)}
    holder["output"] = out


async def run_actions(
    actions: list[dict],
    result: ActionBatchResult,
    *,
    state,
    session,
    agent,
    env,
    thread_id,
    target_cwd,
    mode,
    approval_actions,
    group_tools,
    tool_call_budget,
    mcp_dispatch,
    activity_log,
    subagent_runs,
    update_activity,
    control,
    approval_policy,
    tracer=None,
):
    """Run ``actions`` in order, yielding SSE event strings; fills ``result`` as it goes.

    ``control`` is the turn's `TurnControl`; ``approval_policy`` answers approval requests;
    ``tracer`` (optional `TurnTracer`) records a tool span per action. Stops early when the
    conversation is interrupted.
    """
    for act in actions:
        await control.wait_if_paused()
        if control.interrupted:
            break
        act_id = f"act_{uuid.uuid4().hex[:8]}"
        # Shell actions carry only `command`; name them so events, approvals, and the UI show "bash".
        tool_name = act.get("tool_name") or ("bash" if "command" in act else "")
        label = _TOOL_LABELS.get(tool_name, "终端命令" if not tool_name else tool_name)
        activity_log.append({"id": act_id, "kind": "tool", "label": label, "detail": "执行中", "status": "working"})
        yield f"event: tool_call\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act}, ensure_ascii=False)}\n\n"
        category = permission_category(act, str(target_cwd))
        if tracer:
            tracer.tool_started(act_id, tool_name, act, category)

        out, activity_status, activity_detail = None, "error", ""
        attempt_key, budget_error = reserve_tool_call(tool_call_budget, act)
        if budget_error:
            out, activity_detail = _budget_rejection(budget_error, result)
        elif session.group_id and isinstance(group_tools, list) and tool_name not in group_tools:
            out, activity_detail = group_denied_output(tool_name), "不在该窗口的工具权限内"
        elif tool_name not in _MEMORY_TOOLS and requires_approval(mode, category, act, approval_actions):
            update_activity(act_id, "approval", "等待用户审批")
            message = f"High-risk operation ({tool_name}) requires approval."
            yield approval_required_event(act_id, tool_name, act, message)
            choice = await approval_policy.decide(thread_id=thread_id, action_id=act_id, action=act, category=category)
            if tracer:
                tracer.tool_approval(act_id, choice)
            rejection = _approval_rejection(choice)
            if rejection:
                out, activity_status, activity_detail = rejection

        if out is None:
            holder: dict[str, Any] = {}
            async for event in _execute_action(
                act,
                tool_name,
                holder,
                state=state,
                agent=agent,
                env=env,
                thread_id=thread_id,
                mcp_dispatch=mcp_dispatch,
                subagent_runs=subagent_runs,
            ):
                yield event
            out = holder["output"]
            record_tool_result(tool_call_budget, attempt_key, out)
            succeeded = out.get("returncode", 0) == 0
            activity_status, activity_detail = ("done", "已完成") if succeeded else ("error", "执行失败")

        result.outputs.append(out)
        update_activity(act_id, activity_status, activity_detail)
        if tracer:
            tracer.tool_finished(act_id, out)
        yield tool_result_event(act_id, tool_name, str(out.get("output", ""))[:5000], out.get("returncode", 0))

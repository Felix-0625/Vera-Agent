"""Execute the tool actions returned by one model step and stream their SSE events.

For each action: enforce the tool budget, the group role's allowed tools, and the permission
policy (asking the user through `approval_required` when needed), then run it: user memory,
subagent delegation, web tools, MCP tools, or the local environment (files and shell).
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
    wait_if_paused,
):
    """Run ``actions`` in order, yielding SSE event strings; fills ``result`` as it goes.

    Stops early when the conversation is interrupted.
    """
    for act in actions:
        await wait_if_paused()
        if state.interruption_flags.get(thread_id, False):
            break

        act_id = f"act_{uuid.uuid4().hex[:8]}"
        # Shell actions carry only `command`; name them so events, approvals, and the UI show "bash".
        tool_name = act.get("tool_name") or ("bash" if "command" in act else "")
        tool_labels = {
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
        activity_log.append(
            {
                "id": act_id,
                "kind": "tool",
                "label": tool_labels.get(tool_name, "终端命令" if not tool_name else tool_name),
                "detail": "执行中",
                "status": "working",
            }
        )

        yield f"event: tool_call\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act}, ensure_ascii=False)}\n\n"

        attempt_key, budget_error = reserve_tool_call(tool_call_budget, act)
        if budget_error:
            out = {
                "output": budget_error,
                "returncode": 1,
                "exception_info": "ToolCallLimitExceeded"
                if budget_error.startswith("[Tool call limit")
                else "ToolAttemptLimitExceeded",
            }
            result.outputs.append(out)
            result.tool_limit_reached = out["exception_info"] == "ToolCallLimitExceeded"
            update_activity(
                act_id,
                "error",
                "已达到本轮工具调用上限" if result.tool_limit_reached else "已达到该操作的失败重试上限",
            )
            yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
            continue

        # Confirmation Gating
        category = permission_category(act, str(target_cwd))
        if session.group_id and isinstance(group_tools, list):
            effective_tool = tool_name or ("bash" if "command" in act else "")
            if effective_tool not in group_tools:
                out = {
                    "output": f"[Group role denied] Tool '{effective_tool or 'unknown'}' is not allowed for this conversation window.",
                    "returncode": 1,
                    "exception_info": "GroupToolDenied",
                }
                result.outputs.append(out)
                update_activity(act_id, "error", "不在该窗口的工具权限内")
                yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                continue
        needs_confirm = tool_name not in {"remember_user", "forget_user_memory"} and requires_approval(
            mode, category, act, approval_actions
        )
        if needs_confirm:
            update_activity(act_id, "approval", "等待用户审批")
            yield f"event: approval_required\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act, 'message': f'High-risk operation ({tool_name}) requires approval.'}, ensure_ascii=False)}\n\n"

            fut = asyncio.get_running_loop().create_future()
            pending_key = f"{thread_id}:{act_id}"
            state.pending_approvals[pending_key] = fut

            try:
                choice = await asyncio.wait_for(fut, timeout=300.0)
            except asyncio.TimeoutError:
                choice = "N"
            finally:
                state.pending_approvals.pop(pending_key, None)

            if choice.upper().startswith("N"):
                out = {
                    "output": "[Approval Rejected] Operation rejected by user.",
                    "returncode": 1,
                    "exception_info": "Approval Rejected",
                }
                result.outputs.append(out)
                update_activity(act_id, "error", "用户拒绝")
                yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                continue
            elif choice.upper().startswith("O:"):
                feedback = choice[2:].strip()
                out = {
                    "output": f"[User Override/Correction]: {feedback}",
                    "returncode": 1,
                    "exception_info": "",
                }
                result.outputs.append(out)
                update_activity(act_id, "done", "已提交修改意见")
                yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                continue

        # Execute tool in environment
        try:
            if tool_name == "remember_user":
                arguments = act.get("arguments", {})
                memory = upsert_user_memory(
                    state,
                    str(arguments.get("category", "")),
                    str(arguments.get("content", "")),
                    memory_id=str(arguments["memory_id"]) if arguments.get("memory_id") else None,
                    source_thread_id=thread_id,
                    require_existing=bool(arguments.get("memory_id")),
                )
                out = {
                    "output": f"已保存用户记忆：{memory['content']}",
                    "returncode": 0,
                    "extra": {"memory_id": memory["id"]},
                }
            elif tool_name == "forget_user_memory":
                memory_id = str(act.get("arguments", {}).get("memory_id", ""))
                deleted = bool(memory_id) and delete_user_memory(state, memory_id)
                out = {
                    "output": "已删除指定的用户记忆。" if deleted else "没有找到对应的用户记忆。",
                    "returncode": 0 if deleted else 1,
                }
            elif tool_name in {"delegate_research", "delegate_review"}:
                relay_result: dict[str, Any] = {}
                async for subagent_event in relay_subagent(
                    agent.execute_subagent_tool, act, subagent_runs, relay_result
                ):
                    yield subagent_event
                out = relay_result["output"]
            elif tool_name in {"web_search", "fetch_web_page"}:
                out = await asyncio.to_thread(agent.execute_web_tool, act)
            elif tool_name in mcp_dispatch:
                mcp_session, remote_tool_name = mcp_dispatch[tool_name]
                mcp_result = await mcp_session.call_tool(remote_tool_name, arguments=act.get("arguments", {}))
                rendered = []
                for item in mcp_result.content:
                    if getattr(item, "text", None) is not None:
                        rendered.append(item.text)
                    else:
                        rendered.append(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
                out = {
                    "output": "\n".join(rendered)[:5000],
                    "returncode": 1 if mcp_result.isError else 0,
                    "exception_info": "MCP tool returned an error" if mcp_result.isError else "",
                }
            else:
                # Keep the ASGI loop responsive so pause/interrupt and
                # other conversation controls remain actionable while a
                # synchronous environment tool is running.
                out = await asyncio.to_thread(env.execute, act)
            if "exception_info" not in out:
                out["exception_info"] = ""
        except Exception as e:
            out = {"output": f"Execution error: {e}", "returncode": -1, "exception_info": str(e)}

        record_tool_result(tool_call_budget, attempt_key, out)

        result.outputs.append(out)
        clean_output = str(out.get("output", ""))[:5000]
        update_activity(
            act_id,
            "done" if out.get("returncode", 0) == 0 else "error",
            "已完成" if out.get("returncode", 0) == 0 else "执行失败",
        )
        yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': clean_output, 'returncode': out.get('returncode', 0)}, ensure_ascii=False)}\n\n"

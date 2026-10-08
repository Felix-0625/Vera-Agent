"""Module 1: Agent Execution & Streaming Chat (SSE, HITL approval, interrupt)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.chat")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def chat_stream(request: Request) -> StreamingResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    thread_id = body.get("thread_id") or f"th_{uuid.uuid4().hex[:10]}"
    content = body.get("content", "").strip()
    model_id = body.get("model_id")
    mode = body.get("mode", "confirm")  # "confirm" | "yolo" | "human"
    rule_trigger = body.get("rule_trigger")  # "goal" | "plan" | None
    attached_skills = body.get("attached_skills") or []
    attached_mcps = body.get("attached_mcps") or []

    state.interruption_flags[thread_id] = False

    session = state.get_or_create_session(thread_id)
    if body.get("group_id") and not session.group_id:
        session.group_id = body["group_id"]
        if state.graph:
            state.graph.attach_session_to_group(thread_id, session.group_id)

    # Working directory: Worktree path of attached group if present, otherwise root_path
    target_cwd = state.root_path
    if session.group_id and state.graph and session.group_id in state.graph.groups:
        target_cwd = state.graph.groups[session.group_id].worktree_path

    env = LocalEnvironment(cwd=str(target_cwd))

    # Model configuration resolution
    models_cfg = state.load_json_config("models_config.json", {})
    selected_model_name = "deepseek/deepseek-chat"
    if model_id:
        selected_model_name = model_id
    elif models_cfg.get("models"):
        for m in models_cfg["models"]:
            if m.get("is_default"):
                selected_model_name = m.get("name") or selected_model_name
                break

    model = LitellmModel(
        model_name=selected_model_name,
        allow_empty_tool_calls=True,
    )

    # Permission whitelist check
    perm_cfg = state.load_json_config("permissions_config.json", {
        "default_mode": "confirm",
        "whitelist_actions": ["read", "symbol_search", "check_syntax"],
    })
    whitelist = perm_cfg.get("whitelist_actions", ["read", "symbol_search", "check_syntax"])

    # Construct Agent
    system_prompt = (
        "You are an expert AI software engineer operating in an isolated GitFlow environment. "
        "Use write tool to create new files, edit tool to update existing files, read to inspect, and bash to test. "
        "Direct all diagnostic logs to stderr and keep answers concise."
    )
    if rule_trigger == "plan":
        system_prompt += "\n[PLAN MODE TRIGGERED]: Outline architecture and proposed file changes explicitly before touching code."
    elif rule_trigger == "goal":
        system_prompt += "\n[GOAL MODE TRIGGERED]: Execute autonomously until all acceptance criteria and tests pass."

    if state.skill_mgr:
        for sk_name in attached_skills:
            sk_text = state.skill_mgr.render_skill_instruction(sk_name)
            if sk_text:
                system_prompt += f"\n\n{sk_text}"

    agent = DefaultAgent(
        model=model,
        env=env,
        session=session,
        role=session.role,
        system_template=system_prompt,
        instance_template="{{task}}",
        complete_on_empty_actions=True,
        step_limit=15,
    )

    async def sse_event_generator():
        start_time = time.time()
        step_counter = 0

        if session.group_id and state.registry_mgr:
            state.registry_mgr.update_agent_status(session.group_id, thread_id, "running")

        # 1. Yield initial thinking status
        yield f"event: thinking\ndata: {json.dumps({'step': 0, 'content': 'Analyzing instructions and preparing execution...'}, ensure_ascii=False)}\n\n"

        # Append user turn to session
        if content:
            session.add_messages({
                "role": "user",
                "content": content,
                "extra": {
                    "rule_trigger": rule_trigger,
                    "attached_skills": attached_skills,
                    "attached_mcps": attached_mcps,
                },
            })

        while not state.interruption_flags.get(thread_id, False):
            step_counter += 1
            yield f"event: thinking\ndata: {json.dumps({'step': step_counter, 'content': f'Executing step {step_counter}...'}, ensure_ascii=False)}\n\n"

            try:
                chat_history = session.get_chat_history(prune_stale_observations=True)
                model_msg = model.query(chat_history, tools=agent.get_tools())
                session.add_messages(model_msg)
            except Exception as e:
                yield f"event: text_chunk\ndata: {json.dumps({'content': f'Model inference error: {e}'}, ensure_ascii=False)}\n\n"
                break

            actions = model_msg.get("extra", {}).get("actions", [])
            response_content = model_msg.get("content", "")

            if response_content:
                yield f"event: text_chunk\ndata: {json.dumps({'content': response_content}, ensure_ascii=False)}\n\n"

            if not actions:
                break

            # Execute actions
            outputs = []
            for act in actions:
                if state.interruption_flags.get(thread_id, False):
                    break

                act_id = f"act_{uuid.uuid4().hex[:8]}"
                tool_name = act.get("tool_name", "")

                yield f"event: tool_call\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'args': act}, ensure_ascii=False)}\n\n"

                # Confirmation Gating
                needs_confirm = (mode == "human") or (mode == "confirm" and tool_name not in whitelist)
                if needs_confirm:
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
                        outputs.append(out)
                        yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                        continue
                    elif choice.upper().startswith("O:"):
                        feedback = choice[2:].strip()
                        out = {
                            "output": f"[User Override/Correction]: {feedback}",
                            "returncode": 1,
                            "exception_info": "",
                        }
                        outputs.append(out)
                        yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': out['output'], 'returncode': 1}, ensure_ascii=False)}\n\n"
                        continue

                # Execute tool in environment
                try:
                    out = env.execute(act)
                    if "exception_info" not in out:
                        out["exception_info"] = ""
                except Exception as e:
                    out = {"output": f"Execution error: {e}", "returncode": -1, "exception_info": str(e)}

                outputs.append(out)
                clean_output = str(out.get("output", ""))[:5000]
                yield f"event: tool_result\ndata: {json.dumps({'action_id': act_id, 'tool_name': tool_name, 'output': clean_output, 'returncode': out.get('returncode', 0)}, ensure_ascii=False)}\n\n"

            obs_msgs = model.format_observation_messages(model_msg, outputs, agent.get_template_vars())
            session.add_messages(*obs_msgs)

            if step_counter >= 15:
                break

        # Persist session state
        session.save(state.get_sessions_dir() / f"{thread_id}.json")
        if session.group_id and state.registry_mgr:
            state.registry_mgr.update_agent_status(session.group_id, thread_id, "idle")

        duration = round(time.time() - start_time, 2)
        finish_payload = {
            "duration": duration,
            "steps": step_counter,
            "cost": round(agent.cost, 4),
            "total_cost": round(session.cost, 4),
            "exit_status": "interrupted" if state.interruption_flags.get(thread_id) else "finish",
        }
        yield f"event: finish\ndata: {json.dumps(finish_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def chat_confirm(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    thread_id = body.get("thread_id")
    action_id = body.get("action_id")
    choice = body.get("choice", "Y")

    if not thread_id or not action_id:
        return JSONResponse({"error": "thread_id and action_id required"}, status_code=400)

    key = f"{thread_id}:{action_id}"
    if key in state.pending_approvals and not state.pending_approvals[key].done():
        state.pending_approvals[key].set_result(choice)
        return JSONResponse({"status": "ok", "choice": choice})

    return JSONResponse({"error": "No pending approval for this action"}, status_code=404)


async def chat_interrupt(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    thread_id = body.get("thread_id")
    if not thread_id:
        return JSONResponse({"error": "thread_id required"}, status_code=400)

    state.interruption_flags[thread_id] = True
    for k, fut in list(state.pending_approvals.items()):
        if k.startswith(f"{thread_id}:") and not fut.done():
            fut.set_result("N")

    return JSONResponse({"status": "ok", "interrupted": True})


chat_routes = [
    Route("/api/chat/stream", chat_stream, methods=["POST"]),
    Route("/api/chat/confirm", chat_confirm, methods=["POST"]),
    Route("/api/chat/interrupt", chat_interrupt, methods=["POST"]),
]

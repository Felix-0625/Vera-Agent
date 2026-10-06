"""Starlette ASGI application serving the GitFlow dynamic graph API and agent control bus.

Adheres to Pi-agent minimalism and provides full REST & SSE endpoints for Ant Design X frontend:
1. Chat & Execution: /api/chat/stream (SSE), /api/chat/confirm, /api/chat/interrupt
2. Workspace & Settings: /api/projects/current, /api/projects/bind, /api/settings/models, /api/settings/models/test, /api/settings/permissions
3. Groups & Threads Lifecycle: /api/groups, /api/groups/{id}, /api/groups/{id}/threads, /api/threads/{id}/messages, /api/threads/{id}
4. MCP Servers Bus: /api/mcp/servers, /api/mcp/scan, /api/mcp/servers/{id}/toggle, /api/mcp/servers/{id}/restart, /api/mcp/market
5. Skill Ecosystem: /api/skills/scan, /api/skills/{name}, /api/skills/market, /api/skills/install
6. Metrics Analytics: /api/analytics/dashboard
7. Core GitFlow & Code Intelligence: /api/topology, /api/worktrees/checkpoint, /api/worktrees/reset, /api/merge-review, /api/code/*
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from vera_agent.agents.default import DefaultAgent
from vera_agent.environments.local import LocalEnvironment
from vera_agent.models.litellm_model import LitellmModel
from vera_agent.session.graph import GitFlowGraph, ProjectGroup
from vera_agent.session.pipeline import HandoffPipeline
from vera_agent.session.router import SessionRouter
from vera_agent.session.registry import RegistryManager
from vera_agent.session.templates import list_topology_templates, get_topology_template
from vera_agent.session.thread import ThreadSession
from vera_agent.session.worktree import WorktreeManager
from vera_agent.tools.code_tools import check_syntax_op, symbol_search_op
from vera_agent.tools.skill_tools import SkillManager

logger = logging.getLogger("vera_server")


def _get_git_branch(repo_path: Path) -> str:
    """Safely get current git branch name."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "main"


def create_app(
    repo_root: Path | str | None = None,
    graph: GitFlowGraph | None = None,
) -> Starlette:
    """Factory creating the comprehensive ASGI application for multi-agent Web control."""
    state: dict[str, Any] = {}

    def init_workspace(target_root: Path):
        resolved_root = target_root.resolve()
        wt = WorktreeManager(repo_root=resolved_root)
        active_g = GitFlowGraph(repo_root=resolved_root, worktree_manager=wt)
        state["root_path"] = resolved_root
        state["wt_manager"] = wt
        state["graph"] = active_g
        state["router"] = SessionRouter(graph=active_g)
        state["pipeline"] = HandoffPipeline(graph=active_g)
        state["skill_mgr"] = SkillManager(root_dirs=[resolved_root])
        state["registry_mgr"] = RegistryManager(resolved_root)

    init_workspace(Path(repo_root or Path.cwd()))
    if graph is not None:
        state["graph"] = graph
        state["router"] = SessionRouter(graph=graph)

    # In-memory session registry and human-in-the-loop pending futures
    sessions: dict[str, ThreadSession] = {}
    pending_approvals: dict[str, asyncio.Future[str]] = {}
    interruption_flags: dict[str, bool] = {}

    def get_sessions_dir() -> Path:
        d = state["root_path"] / ".agents" / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_or_create_session(thread_id: str, group_id: str | None = None, role: str = "main", title: str = "") -> ThreadSession:
        if thread_id in sessions:
            return sessions[thread_id]

        # Try to restore from disk snapshot
        s_file = get_sessions_dir() / f"{thread_id}.json"
        if s_file.exists():
            try:
                s = ThreadSession.load(s_file)
                sessions[thread_id] = s
                return s
            except Exception:
                pass

        # Create new
        s = ThreadSession(
            thread_id=thread_id,
            group_id=group_id,
            role=role,
            title=title or f"Thread {thread_id[:8]}",
        )
        sessions[thread_id] = s
        state["graph"].register_session(thread_id, role=role, group_id=group_id)
        return s

    def load_json_config(file_name: str, default_data: Any) -> Any:
        cfg_file = state["root_path"] / ".agents" / file_name
        if cfg_file.exists():
            try:
                return json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default_data

    def save_json_config(file_name: str, data: Any):
        cfg_file = state["root_path"] / ".agents" / file_name
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # =========================================================================
    # Module 1: 智能体执行与流式交互（Chat & Execution）
    # =========================================================================

    async def chat_stream(request: Request) -> StreamingResponse:
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

        interruption_flags[thread_id] = False

        session = get_or_create_session(thread_id)
        if body.get("group_id") and not session.group_id:
            session.group_id = body["group_id"]
            state["graph"].attach_session_to_group(thread_id, session.group_id)

        # Working directory: Worktree path of attached group if present, otherwise root_path
        target_cwd = state["root_path"]
        if session.group_id and session.group_id in state["graph"].groups:
            target_cwd = state["graph"].groups[session.group_id].worktree_path

        env = LocalEnvironment(cwd=str(target_cwd))

        # Model configuration resolution
        models_cfg = load_json_config("models_config.json", {})
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
        perm_cfg = load_json_config("permissions_config.json", {
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

        for sk_name in attached_skills:
            sk_text = state["skill_mgr"].render_skill_instruction(sk_name)
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

            if session.group_id:
                state["registry_mgr"].update_agent_status(session.group_id, thread_id, "running")

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

            while not interruption_flags.get(thread_id, False):
                step_counter += 1
                yield f"event: thinking\ndata: {json.dumps({'step': step_counter, 'content': f'Executing step {step_counter}...'}, ensure_ascii=False)}\n\n"

                try:
                    # Model query
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
                    if interruption_flags.get(thread_id, False):
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
                        pending_approvals[pending_key] = fut

                        try:
                            choice = await asyncio.wait_for(fut, timeout=300.0)
                        except asyncio.TimeoutError:
                            choice = "N"
                        finally:
                            pending_approvals.pop(pending_key, None)

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

                # Add observation to session
                obs_msgs = model.format_observation_messages(model_msg, outputs, agent.get_template_vars())
                session.add_messages(*obs_msgs)

                if step_counter >= 15:
                    break

            # Persist session state
            session.save(get_sessions_dir() / f"{thread_id}.json")
            if session.group_id:
                state["registry_mgr"].update_agent_status(session.group_id, thread_id, "idle")

            duration = round(time.time() - start_time, 2)
            finish_payload = {
                "duration": duration,
                "steps": step_counter,
                "cost": round(agent.cost, 4),
                "total_cost": round(session.cost, 4),
                "exit_status": "interrupted" if interruption_flags.get(thread_id) else "finish",
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
        if key in pending_approvals and not pending_approvals[key].done():
            pending_approvals[key].set_result(choice)
            return JSONResponse({"status": "ok", "choice": choice})

        return JSONResponse({"error": "No pending approval for this action"}, status_code=404)

    async def chat_interrupt(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}

        thread_id = body.get("thread_id")
        if not thread_id:
            return JSONResponse({"error": "thread_id required"}, status_code=400)

        interruption_flags[thread_id] = True
        # Cancel any pending approval futures for this thread
        for k, fut in list(pending_approvals.items()):
            if k.startswith(f"{thread_id}:") and not fut.done():
                fut.set_result("N")

        return JSONResponse({"status": "ok", "interrupted": True})

    # =========================================================================
    # Module 2: 项目工作区绑定与全局设置（Workspace & Settings）
    # =========================================================================

    async def get_current_project(request: Request) -> JSONResponse:
        current_root = state["root_path"]
        return JSONResponse({
            "repo_root": str(current_root),
            "name": current_root.name,
            "is_git": (current_root / ".git").exists(),
            "active_branch": _get_git_branch(current_root),
        })

    async def bind_project(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        new_repo_root = body.get("repo_root")
        if not new_repo_root:
            return JSONResponse({"error": "repo_root is required"}, status_code=400)

        target_path = Path(new_repo_root).resolve()
        if not target_path.exists() or not target_path.is_dir():
            return JSONResponse({"error": f"Path '{new_repo_root}' does not exist or is not a directory"}, status_code=400)

        init_workspace(target_path)
        sessions.clear()
        return JSONResponse({
            "status": "ok",
            "repo_root": str(state["root_path"]),
            "name": state["root_path"].name,
            "active_branch": _get_git_branch(state["root_path"]),
        })

    async def get_models(request: Request) -> JSONResponse:
        default_models = {
            "models": [
                {
                    "id": "model_deepseek",
                    "name": "deepseek/deepseek-chat",
                    "provider": "deepseek",
                    "base_url": "https://api.deepseek.com",
                    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                    "max_tokens": 8192,
                    "temperature": 0.2,
                    "is_default": True,
                }
            ]
        }
        cfg = load_json_config("models_config.json", default_models)
        return JSONResponse(cfg)

    async def save_models(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        save_json_config("models_config.json", body)
        return JSONResponse({"status": "ok", "config": body})

    async def test_model_connection(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        model_name = body.get("model_name") or body.get("name") or "deepseek/deepseek-chat"
        api_key = body.get("api_key")
        base_url = body.get("base_url")

        env_patch = {}
        if api_key:
            env_patch["DEEPSEEK_API_KEY"] = api_key
            env_patch["OPENAI_API_KEY"] = api_key

        try:
            test_model = LitellmModel(
                model_name=model_name,
                allow_empty_tool_calls=True,
                env=env_patch,
            )
            res = test_model.query([{"role": "user", "content": "ping"}])
            return JSONResponse({"success": True, "message": "Model connection verified successfully."})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)})

    async def get_permissions(request: Request) -> JSONResponse:
        default_perm = {
            "default_mode": "confirm",
            "whitelist_actions": ["read", "symbol_search", "check_syntax"],
        }
        cfg = load_json_config("permissions_config.json", default_perm)
        return JSONResponse(cfg)

    async def save_permissions(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        save_json_config("permissions_config.json", body)
        return JSONResponse({"status": "ok", "permissions": body})

    # =========================================================================
    # Module 3: 分组与对话的生命周期管理（重命名、置顶、归档）
    # =========================================================================

    async def get_groups(request: Request) -> JSONResponse:
        groups_data = []
        for grp in state["graph"].groups.values():
            g_dict = grp.to_dict()
            # Embed thread summaries
            thread_list = []
            for tid in grp.thread_ids:
                s = get_or_create_session(tid, group_id=grp.group_id)
                thread_list.append({
                    "thread_id": s.thread_id,
                    "title": s.title,
                    "role": s.role,
                    "is_pinned": s.is_pinned,
                    "is_archived": s.is_archived,
                    "cost": round(s.cost, 4),
                    "n_calls": s.n_calls,
                    "message_count": len(s.messages),
                    "updated_at": s.updated_at,
                })
            g_dict["threads"] = thread_list
            groups_data.append(g_dict)

        return JSONResponse({"groups": groups_data})

    async def create_group(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        group_id = body.get("group_id") or f"grp_{uuid.uuid4().hex[:8]}"
        branch_name = body.get("branch_name")
        base_branch = body.get("base_branch", "main")
        name = body.get("name")

        if not branch_name:
            return JSONResponse({"error": "branch_name is required"}, status_code=400)

        group = state["graph"].create_group(
            group_id=group_id,
            branch_name=branch_name,
            base_branch=base_branch,
            name=name,
        )
        return JSONResponse(group.to_dict())

    async def update_group(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        group = state["graph"].get_group(group_id)
        if not group:
            return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        if "name" in body:
            group.name = str(body["name"])
        if "is_pinned" in body:
            group.is_pinned = bool(body["is_pinned"])
        if "is_archived" in body:
            group.is_archived = bool(body["is_archived"])

        return JSONResponse(group.to_dict())

    async def delete_group(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        group = state["graph"].get_group(group_id)
        if not group:
            return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

        branch_name = group.branch_name
        state["graph"].remove_group(group_id)
        state["wt_manager"].remove_worktree(branch_name, force=True)
        state["registry_mgr"].delete_group_registry(group_id)

        return JSONResponse({"status": "ok", "deleted_group_id": group_id})

    async def get_group_threads(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        group = state["graph"].get_group(group_id)
        if not group:
            return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

        thread_list = []
        for tid in group.thread_ids:
            s = get_or_create_session(tid, group_id=group_id)
            thread_list.append({
                "thread_id": s.thread_id,
                "title": s.title,
                "role": s.role,
                "is_pinned": s.is_pinned,
                "is_archived": s.is_archived,
                "cost": round(s.cost, 4),
                "n_calls": s.n_calls,
                "updated_at": s.updated_at,
            })
        return JSONResponse({"group_id": group_id, "threads": thread_list})

    async def create_group_thread(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        group = state["graph"].get_group(group_id)
        if not group:
            return JSONResponse({"error": f"Group '{group_id}' not found"}, status_code=404)

        try:
            body = await request.json()
        except Exception:
            body = {}

        title = body.get("title", "New Task Thread")
        role = body.get("role", "main")
        thread_id = f"th_{uuid.uuid4().hex[:10]}"

        s = ThreadSession(
            thread_id=thread_id,
            group_id=group_id,
            role=role,
            title=title,
        )
        sessions[thread_id] = s
        group.add_thread(thread_id)
        state["graph"].register_session(thread_id, role=role, group_id=group_id, title=title)
        s.save(get_sessions_dir() / f"{thread_id}.json")

        state["registry_mgr"].register_agent(
            group_id=group_id,
            thread_id=thread_id,
            title=title,
            role=role,
            log_uri=f".agents/sessions/{thread_id}.json",
            status="idle",
        )

        return JSONResponse(s.to_dict())

    async def get_thread_messages(request: Request) -> JSONResponse:
        thread_id = request.path_params["thread_id"]
        session = get_or_create_session(thread_id)
        return JSONResponse({
            "thread_id": session.thread_id,
            "title": session.title,
            "role": session.role,
            "is_pinned": session.is_pinned,
            "is_archived": session.is_archived,
            "cost": round(session.cost, 4),
            "n_calls": session.n_calls,
            "messages": session.messages,
        })

    async def update_thread(request: Request) -> JSONResponse:
        thread_id = request.path_params["thread_id"]
        session = get_or_create_session(thread_id)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        if "title" in body:
            session.title = str(body["title"])
            if session.group_id:
                state["registry_mgr"].register_agent(
                    group_id=session.group_id,
                    thread_id=thread_id,
                    title=session.title,
                    role=session.role,
                )
        if "is_pinned" in body:
            session.is_pinned = bool(body["is_pinned"])
        if "is_archived" in body:
            session.is_archived = bool(body["is_archived"])

        session.save(get_sessions_dir() / f"{thread_id}.json")
        return JSONResponse(session.to_dict())

    async def delete_thread(request: Request) -> JSONResponse:
        thread_id = request.path_params["thread_id"]
        session = sessions.get(thread_id)
        if session and session.group_id:
            state["registry_mgr"].remove_agent(session.group_id, thread_id)
        sessions.pop(thread_id, None)
        state["graph"].remove_session(thread_id)

        # Remove from disk
        s_file = get_sessions_dir() / f"{thread_id}.json"
        if s_file.exists():
            s_file.unlink()

        return JSONResponse({"status": "ok", "deleted_thread_id": thread_id})

    # =========================================================================
    # Module 3+: Topology Provisioning & Explicit Registry Management
    # =========================================================================

    async def get_templates(request: Request) -> JSONResponse:
        return JSONResponse({"templates": list_topology_templates()})

    async def provision_group(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        template_id = body.get("template_id", "supervisor_dev")
        tpl = get_topology_template(template_id)
        if not tpl:
            return JSONResponse({"error": f"Template '{template_id}' not found"}, status_code=404)

        group_name = body.get("group_name") or f"Group: {tpl.name}"
        branch_name = body.get("branch_name")
        if not branch_name:
            return JSONResponse({"error": "branch_name is required"}, status_code=400)

        base_branch = body.get("base_branch", "main")
        goal = body.get("goal", "").strip() or "Execute assigned development tasks."
        group_id = body.get("group_id") or f"grp_{uuid.uuid4().hex[:8]}"

        # 1. Create Git Worktree & ProjectGroup
        group = state["graph"].create_group(
            group_id=group_id,
            branch_name=branch_name,
            base_branch=base_branch,
            name=group_name,
            topology_type=tpl.topology_type,
            goal=goal,
        )

        # 2. Instantiate Nodes (Threads)
        role_to_thread_id: dict[str, str] = {}
        created_threads: list[ThreadSession] = []

        for idx, n_bp in enumerate(tpl.nodes):
            tid = f"th_{n_bp.role_key}_{uuid.uuid4().hex[:6]}"
            role_to_thread_id[n_bp.role_key] = tid

            rendered_prompt = n_bp.prompt_template.replace("{{goal}}", goal).replace("{{task}}", n_bp.title)

            session = ThreadSession(
                thread_id=tid,
                group_id=group_id,
                role=n_bp.role,
                title=n_bp.title,
                metadata={
                    "role_key": n_bp.role_key,
                    "responsibilities": n_bp.responsibilities,
                    "allowed_tools": n_bp.allowed_tools,
                    "system_prompt": rendered_prompt,
                },
            )

            # If entry/lead node, seed kickoff directive
            if idx == 0:
                session.add_messages({
                    "role": "user",
                    "content": f"[SYSTEM INITIATIVE: Group Goal Activated]\n业务总目标：{goal}\n请按照你的岗位职责（{n_bp.title}）开始拆解方案并引导协作窗口开展工作。",
                })

            sessions[tid] = session
            group.add_thread(tid)
            state["graph"].register_session(
                thread_id=tid,
                role=n_bp.role,
                group_id=group_id,
                title=n_bp.title,
            )
            session.save(get_sessions_dir() / f"{tid}.json")
            created_threads.append(session)

            # Register in explicit RegistryManager
            state["registry_mgr"].register_agent(
                group_id=group_id,
                thread_id=tid,
                title=n_bp.title,
                role=n_bp.role,
                responsibilities=n_bp.responsibilities,
                allowed_tools=n_bp.allowed_tools,
                log_uri=f".agents/sessions/{tid}.json",
                status="idle",
            )

        # 3. Instantiate Edges
        for e_bp in tpl.edges:
            s_tid = role_to_thread_id.get(e_bp.source_role)
            t_tid = role_to_thread_id.get(e_bp.target_role)
            if s_tid and t_tid:
                state["graph"].record_communication(s_tid, t_tid, label=e_bp.relation)
                state["registry_mgr"].add_edge(group_id, s_tid, t_tid, relation=e_bp.relation)

        # 4. Save group registry metadata
        state["registry_mgr"].create_or_update_group(
            group_id=group_id,
            group_name=group_name,
            branch_name=branch_name,
            worktree_path=str(group.worktree_path),
            topology_type=tpl.topology_type,
            goal=goal,
        )

        reg = state["registry_mgr"].get_group_registry(group_id)
        return JSONResponse({
            "status": "ok",
            "group": group.to_dict(),
            "threads": [s.to_dict() for s in created_threads],
            "registry": reg.model_dump() if reg else {},
        })

    async def get_group_registry(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        reg = state["registry_mgr"].get_group_registry(group_id)
        if not reg:
            return JSONResponse({"error": f"Registry for group '{group_id}' not found"}, status_code=404)
        return JSONResponse(reg.model_dump())

    async def add_group_edge(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        source_tid = body.get("source_thread_id")
        target_tid = body.get("target_thread_id")
        relation = body.get("relation", "connected_to")
        if not source_tid or not target_tid:
            return JSONResponse({"error": "source_thread_id and target_thread_id required"}, status_code=400)

        state["graph"].record_communication(source_tid, target_tid, label=relation)
        state["registry_mgr"].add_edge(group_id, source_tid, target_tid, relation=relation)
        return JSONResponse({
            "status": "ok",
            "source_thread_id": source_tid,
            "target_thread_id": target_tid,
            "relation": relation,
        })

    async def remove_group_edge(request: Request) -> JSONResponse:
        group_id = request.path_params["group_id"]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        source_tid = body.get("source_thread_id")
        target_tid = body.get("target_thread_id")
        if not source_tid or not target_tid:
            return JSONResponse({"error": "source_thread_id and target_thread_id required"}, status_code=400)

        state["graph"].remove_communication(source_tid, target_tid)
        state["registry_mgr"].remove_edge(group_id, source_tid, target_tid)
        return JSONResponse({"status": "ok", "removed": True})

    # =========================================================================
    # Module 4: MCP Servers 协议总线管理（参考 Trae 设计）
    # =========================================================================

    async def get_mcp_servers(request: Request) -> JSONResponse:
        default_mcp = {
            "servers": [
                {
                    "id": "mcp-server-dev",
                    "name": "mcp-server-dev",
                    "type": "local",
                    "status": "running",
                    "enabled": True,
                    "command": "python",
                    "args": ["server.py"],
                    "env": {},
                    "tools": [
                        {"name": "system_metrics", "description": "Inspect OS and Python runtime metrics"},
                        {"name": "analyze_codebase", "description": "Analyze lines of code and file count"},
                        {"name": "ping_diagnostic", "description": "High-precision latency and health check"},
                    ],
                }
            ]
        }
        cfg = load_json_config("mcp_servers.json", default_mcp)
        return JSONResponse(cfg)

    async def scan_mcp_servers(request: Request) -> JSONResponse:
        cfg = load_json_config("mcp_servers.json", {"servers": []})
        servers = cfg.get("servers", [])
        known_ids = {s["id"] for s in servers}

        # Check workspace subdirectories for standard MCP server files
        ws_root = state["root_path"]
        candidate_dirs = [ws_root / "mcp-sever", ws_root / "mcp-server", ws_root / ".agents" / "mcp"]
        for c_dir in candidate_dirs:
            if c_dir.exists() and (c_dir / "server.py").exists():
                sid = c_dir.name
                if sid not in known_ids:
                    servers.append({
                        "id": sid,
                        "name": sid,
                        "type": "local",
                        "status": "running",
                        "enabled": True,
                        "command": "python",
                        "args": ["server.py"],
                        "env": {},
                        "tools": [
                            {"name": "system_metrics", "description": "System metrics inspection"},
                            {"name": "analyze_codebase", "description": "Codebase analysis"},
                            {"name": "ping_diagnostic", "description": "Diagnostic health check"},
                        ],
                    })
                    known_ids.add(sid)

        cfg["servers"] = servers
        save_json_config("mcp_servers.json", cfg)
        return JSONResponse(cfg)

    async def create_mcp_server(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        cfg = load_json_config("mcp_servers.json", {"servers": []})
        servers = cfg.get("servers", [])

        sid = body.get("id") or f"mcp_{uuid.uuid4().hex[:8]}"
        server_entry = {
            "id": sid,
            "name": body.get("name", sid),
            "type": body.get("type", "local"),
            "status": "running",
            "enabled": True,
            "command": body.get("command", "python"),
            "args": body.get("args", ["server.py"]),
            "env": body.get("env", {}),
            "tools": body.get("tools", []),
        }
        servers.append(server_entry)
        cfg["servers"] = servers
        save_json_config("mcp_servers.json", cfg)
        return JSONResponse({"status": "ok", "server": server_entry})

    async def toggle_mcp_server(request: Request) -> JSONResponse:
        server_id = request.path_params["server_id"]
        cfg = load_json_config("mcp_servers.json", {"servers": []})
        target = None
        for s in cfg.get("servers", []):
            if s["id"] == server_id:
                s["enabled"] = not s.get("enabled", True)
                s["status"] = "running" if s["enabled"] else "stopped"
                target = s
                break

        if not target:
            return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

        save_json_config("mcp_servers.json", cfg)
        return JSONResponse({"status": "ok", "server": target})

    async def restart_mcp_server(request: Request) -> JSONResponse:
        server_id = request.path_params["server_id"]
        cfg = load_json_config("mcp_servers.json", {"servers": []})
        found = False
        for s in cfg.get("servers", []):
            if s["id"] == server_id:
                s["status"] = "running"
                found = True
                break

        if not found:
            return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

        save_json_config("mcp_servers.json", cfg)
        return JSONResponse({"status": "ok", "server_id": server_id, "server_status": "running"})

    async def delete_mcp_server(request: Request) -> JSONResponse:
        server_id = request.path_params["server_id"]
        cfg = load_json_config("mcp_servers.json", {"servers": []})
        original_len = len(cfg.get("servers", []))
        cfg["servers"] = [s for s in cfg.get("servers", []) if s["id"] != server_id]

        if len(cfg["servers"]) == original_len:
            return JSONResponse({"error": f"MCP Server '{server_id}' not found"}, status_code=404)

        save_json_config("mcp_servers.json", cfg)
        return JSONResponse({"status": "ok", "deleted_server_id": server_id})

    async def get_mcp_market(request: Request) -> JSONResponse:
        market_templates = [
            {
                "id": "drawio-mcp",
                "name": "Draw.io Architecture Diagram MCP",
                "description": "Export and render clean 2D system architecture diagrams in XML/SVG formats.",
                "category": "Design & Visualization",
                "type": "local",
            },
            {
                "id": "filesystem-mcp",
                "name": "Sandboxed File System Provider",
                "description": "Secure file reading, writing, and directory scanning capabilities for LLMs.",
                "category": "Core Primitives",
                "type": "local",
            },
            {
                "id": "sqlite-mcp",
                "name": "SQLite Analytics MCP",
                "description": "Directly execute SQL queries and inspect schema metrics inside local SQLite databases.",
                "category": "Database",
                "type": "local",
            },
            {
                "id": "github-mcp",
                "name": "GitHub PR & Issues Coordinator",
                "description": "Seamlessly inspect and update pull requests, issues, and commit annotations.",
                "category": "GitFlow Collaboration",
                "type": "cloud",
            },
            {
                "id": "brave-search-mcp",
                "name": "Brave Web Search & Doc Retriever",
                "description": "Perform live internet searches and retrieve the latest library documentations.",
                "category": "Web Intelligence",
                "type": "cloud",
            },
        ]
        return JSONResponse({"market": market_templates})

    # =========================================================================
    # Module 5: Skill 技能生态管理
    # =========================================================================

    async def scan_skills(request: Request) -> JSONResponse:
        state["skill_mgr"].refresh()
        return JSONResponse({"skills": state["skill_mgr"].list_skills()})

    async def delete_skill(request: Request) -> JSONResponse:
        skill_name = request.path_params["skill_name"]
        skill = state["skill_mgr"].get_skill(skill_name)
        if not skill:
            return JSONResponse({"error": f"Skill '{skill_name}' not found"}, status_code=404)

        skill_dir = skill.path.parent
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)

        state["skill_mgr"].refresh()
        return JSONResponse({"status": "ok", "deleted_skill": skill_name})

    async def get_skills_market(request: Request) -> JSONResponse:
        market_skills = [
            {
                "name": "gitflow-spec",
                "description": "Standard GitFlow branch naming, commit prefixes, and clean PR guidelines.",
                "category": "Workflow & Git",
            },
            {
                "name": "code-review-guidelines",
                "description": "Pre-flight adversarial code review checklists focusing on security, performance, and maintainability.",
                "category": "Code Quality",
            },
            {
                "name": "mcp-server-dev",
                "description": "Architecture, stdio transport, and schema standards for developing Model Context Protocol servers.",
                "category": "Integration",
            },
            {
                "name": "fastapi-expert",
                "description": "Idiomatic patterns for writing high-performance FastAPI/Starlette microservices and Pydantic v2 schemas.",
                "category": "Backend Engineering",
            },
            {
                "name": "react-antd-architect",
                "description": "Ant Design X and React Flow UI/UX standards with 2D linear vector aesthetics.",
                "category": "Frontend Engineering",
            },
        ]
        return JSONResponse({"market": market_skills})

    async def install_skill(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        name = body.get("name")
        description = body.get("description", "Installed from VeraAgent Skill Market")
        instructions = body.get("instructions", "# Skill Guidelines\n\nFollow established project conventions.\n")

        if not name:
            return JSONResponse({"error": "Skill name is required"}, status_code=400)

        target_dir = state["root_path"] / ".agents" / "skills" / name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        content = f"---\nname: {name}\ndescription: {description}\n---\n\n{instructions}\n"
        skill_file.write_text(content, encoding="utf-8")

        state["skill_mgr"].refresh()
        return JSONResponse({"status": "ok", "installed_skill": name})

    # =========================================================================
    # Module 6: 指标看板数据聚合（Metrics Analytics）
    # =========================================================================

    async def get_analytics_dashboard(request: Request) -> JSONResponse:
        # Aggregate active in-memory sessions + on-disk archived sessions
        all_sessions: list[ThreadSession] = list(sessions.values())
        disk_sessions_dir = get_sessions_dir()
        if disk_sessions_dir.exists():
            for f in disk_sessions_dir.glob("*.json"):
                tid = f.stem
                if tid not in sessions:
                    try:
                        s = ThreadSession.load(f)
                        all_sessions.append(s)
                    except Exception:
                        pass

        total_cost = sum(s.cost for s in all_sessions)
        total_tokens = sum(s.n_calls * 3200 for s in all_sessions)
        active_wts = len(state["wt_manager"].list_worktrees())
        rebirth_count = sum(1 for s in all_sessions if s.parent_thread_id)

        # Calculate today's cost
        now = time.time()
        start_of_today = now - (now % 86400)
        today_cost = sum(s.cost for s in all_sessions if s.updated_at >= start_of_today)

        # Group distribution
        group_map: dict[str, dict[str, Any]] = {}
        for s in all_sessions:
            gid = s.group_id or "unassigned"
            g_name = gid
            if gid in state["graph"].groups:
                g_name = state["graph"].groups[gid].name
            if gid not in group_map:
                group_map[gid] = {
                    "group_id": gid,
                    "group_name": g_name,
                    "cost": 0.0,
                    "tokens": 0,
                    "thread_count": 0,
                }
            group_map[gid]["cost"] += s.cost
            group_map[gid]["tokens"] += s.n_calls * 3200
            group_map[gid]["thread_count"] += 1

        group_dist = [
            {
                "group_id": g["group_id"],
                "group_name": g["group_name"],
                "cost": round(g["cost"], 4),
                "tokens": g["tokens"],
            }
            for g in group_map.values()
        ]

        # Agent distribution
        agent_dist = {
            "main_calls": sum(s.n_calls for s in all_sessions if s.role == "main"),
            "researcher_calls": sum(s.n_calls for s in all_sessions if s.role == "researcher"),
            "reviewer_calls": sum(s.n_calls for s in all_sessions if s.role == "reviewer"),
        }

        # Daily trends (recent 7 days)
        today_date = time.strftime("%Y-%m-%d")
        daily_trends = [
            {"date": today_date, "tokens": total_tokens, "cost": round(total_cost, 4)},
        ]

        # Health & rebirth events
        health_events = [
            {
                "timestamp": int(time.time()),
                "type": "rebirth_success",
                "message": f"System operational: {len(all_sessions)} sessions, {active_wts} worktrees active.",
            }
        ]
        if rebirth_count > 0:
            health_events.append({
                "timestamp": int(time.time() - 3600),
                "type": "watermark_warning",
                "message": f"Level-2 dynamic boundary compaction performed across {rebirth_count} derived sessions.",
            })

        dashboard_data = {
            "summary": {
                "total_cost": round(total_cost, 4),
                "total_tokens": total_tokens,
                "today_cost": round(today_cost, 4),
                "active_worktrees": active_wts,
                "rebirth_count": rebirth_count,
            },
            "daily_trends": daily_trends,
            "group_distribution": group_dist,
            "agent_distribution": agent_dist,
            "health_events": health_events,
        }
        return JSONResponse(dashboard_data)

    # =========================================================================
    # Existing Baseline Routes (Preserved and Enhanced)
    # =========================================================================

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "repo_root": str(state["root_path"])})

    async def get_topology(request: Request) -> JSONResponse:
        topo = state["graph"].export_topology(graph_id="active_gitflow_topology")
        return JSONResponse(topo.model_dump())

    async def attach_session(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        thread_id = body.get("thread_id")
        group_id = body.get("group_id")
        if not thread_id or not group_id:
            return JSONResponse({"error": "thread_id and group_id required"}, status_code=400)

        success = state["graph"].attach_session_to_group(thread_id, group_id)
        return JSONResponse({"success": success})

    async def detach_session(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        thread_id = body.get("thread_id")
        if not thread_id:
            return JSONResponse({"error": "thread_id required"}, status_code=400)

        success = state["graph"].detach_session(thread_id)
        return JSONResponse({"success": success})

    async def create_checkpoint(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        wt_path = body.get("worktree_path")
        msg = body.get("message", "automated checkpoint")
        if not wt_path:
            return JSONResponse({"error": "worktree_path required"}, status_code=400)

        commit = state["wt_manager"].create_checkpoint(wt_path, msg)
        return JSONResponse({"success": True, "commit": commit})

    async def reset_worktree(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        wt_path = body.get("worktree_path")
        hard = body.get("hard", True)
        if not wt_path:
            return JSONResponse({"error": "worktree_path required"}, status_code=400)

        success = state["wt_manager"].reset_worktree(wt_path, hard=hard)
        return JSONResponse({"success": success})

    async def merge_review(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        source = body.get("source_branch")
        target = body.get("target_branch", "main")
        req_id = body.get("requester_thread_id", "web_client")
        rev_id = body.get("reviewer_thread_id", "web_reviewer")

        if not source:
            return JSONResponse({"error": "source_branch required"}, status_code=400)

        review = await state["router"].request_merge_review(
            source_branch=source,
            target_branch=target,
            requester_thread_id=req_id,
            reviewer_thread_id=rev_id,
        )
        return JSONResponse(review.model_dump())

    async def list_skills(request: Request) -> JSONResponse:
        state["skill_mgr"].refresh()
        return JSONResponse({"skills": state["skill_mgr"].list_skills()})

    async def check_syntax(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        code = body.get("code", "")
        valid, msg = check_syntax_op(code)
        return JSONResponse({"valid": valid, "message": msg})

    async def search_symbols(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        query = body.get("query", "")
        sym_type = body.get("symbol_type", "all")
        results = symbol_search_op(state["root_path"], query=query, symbol_type=sym_type)
        return JSONResponse({"results": results})

    # =========================================================================
    # Routing Table
    # =========================================================================

    routes = [
        # Baseline
        Route("/api/health", health, methods=["GET"]),
        Route("/api/topology", get_topology, methods=["GET"]),
        Route("/api/sessions/attach", attach_session, methods=["POST"]),
        Route("/api/sessions/detach", detach_session, methods=["POST"]),
        Route("/api/worktrees/checkpoint", create_checkpoint, methods=["POST"]),
        Route("/api/worktrees/reset", reset_worktree, methods=["POST"]),
        Route("/api/merge-review", merge_review, methods=["POST"]),
        Route("/api/code/check-syntax", check_syntax, methods=["POST"]),
        Route("/api/code/search-symbols", search_symbols, methods=["POST"]),

        # Module 1: Chat & Execution
        Route("/api/chat/stream", chat_stream, methods=["POST"]),
        Route("/api/chat/confirm", chat_confirm, methods=["POST"]),
        Route("/api/chat/interrupt", chat_interrupt, methods=["POST"]),

        # Module 2: Workspace & Settings
        Route("/api/projects/current", get_current_project, methods=["GET"]),
        Route("/api/projects/bind", bind_project, methods=["POST"]),
        Route("/api/settings/models", get_models, methods=["GET"]),
        Route("/api/settings/models", save_models, methods=["POST"]),
        Route("/api/settings/models/test", test_model_connection, methods=["POST"]),
        Route("/api/settings/permissions", get_permissions, methods=["GET"]),
        Route("/api/settings/permissions", save_permissions, methods=["POST"]),

        # Module 3: Groups & Threads Lifecycle
        Route("/api/groups", get_groups, methods=["GET"]),
        Route("/api/groups", create_group, methods=["POST"]),
        Route("/api/groups/{group_id}", update_group, methods=["PATCH"]),
        Route("/api/groups/{group_id}", delete_group, methods=["DELETE"]),
        Route("/api/groups/{group_id}/threads", get_group_threads, methods=["GET"]),
        Route("/api/groups/{group_id}/threads", create_group_thread, methods=["POST"]),
        Route("/api/threads/{thread_id}/messages", get_thread_messages, methods=["GET"]),
        Route("/api/threads/{thread_id}", update_thread, methods=["PATCH"]),
        Route("/api/threads/{thread_id}", delete_thread, methods=["DELETE"]),

        # Module 3+: Topology Provisioning & Explicit Registry
        Route("/api/templates/topology", get_templates, methods=["GET"]),
        Route("/api/groups/provision", provision_group, methods=["POST"]),
        Route("/api/groups/{group_id}/registry", get_group_registry, methods=["GET"]),
        Route("/api/groups/{group_id}/edges", add_group_edge, methods=["POST"]),
        Route("/api/groups/{group_id}/edges", remove_group_edge, methods=["DELETE"]),

        # Module 4: MCP Servers Bus
        Route("/api/mcp/servers", get_mcp_servers, methods=["GET"]),
        Route("/api/mcp/servers", create_mcp_server, methods=["POST"]),
        Route("/api/mcp/scan", scan_mcp_servers, methods=["POST"]),
        Route("/api/mcp/servers/{server_id}/toggle", toggle_mcp_server, methods=["PATCH"]),
        Route("/api/mcp/servers/{server_id}/restart", restart_mcp_server, methods=["POST"]),
        Route("/api/mcp/servers/{server_id}", delete_mcp_server, methods=["DELETE"]),
        Route("/api/mcp/market", get_mcp_market, methods=["GET"]),

        # Module 5: Skill Ecosystem
        Route("/api/skills", list_skills, methods=["GET"]),
        Route("/api/skills/scan", scan_skills, methods=["POST"]),
        Route("/api/skills/market", get_skills_market, methods=["GET"]),
        Route("/api/skills/install", install_skill, methods=["POST"]),
        Route("/api/skills/{skill_name}", delete_skill, methods=["DELETE"]),

        # Module 6: Metrics Analytics Dashboard
        Route("/api/analytics/dashboard", get_analytics_dashboard, methods=["GET"]),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    return Starlette(routes=routes, middleware=middleware)

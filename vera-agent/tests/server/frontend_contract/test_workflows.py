"""Workflows regression coverage."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from starlette.testclient import TestClient

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.app import create_app


def test_module3_groups_and_threads_lifecycle(temp_git_repo: Path):
    """Test Module 3: Groups and Threads lifecycle (pin, archive, rename, delete)."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)

    # 1. Create ProjectGroup
    res_create_grp = client.post(
        "/api/groups",
        json={"group_id": "grp_pay", "branch_name": "feat/pay", "base_branch": "main", "name": "Payment Group"},
    )
    assert res_create_grp.status_code == 200
    grp_info = res_create_grp.json()
    assert grp_info["group_id"] == "grp_pay"
    assert grp_info["is_pinned"] is False
    assert grp_info["is_archived"] is False

    # 2. PATCH /api/groups/{group_id} (rename, pin, archive)
    res_patch_grp = client.patch(
        "/api/groups/grp_pay",
        json={"name": "Payment Modernization", "is_pinned": True, "is_archived": False},
    )
    assert res_patch_grp.status_code == 200
    assert res_patch_grp.json()["name"] == "Payment Modernization"
    assert res_patch_grp.json()["is_pinned"] is True

    # 3. POST /api/groups/{group_id}/threads (create thread)
    res_thread = client.post(
        "/api/groups/grp_pay/threads",
        json={"title": "Stripe Webhook Bugfix", "role": "main"},
    )
    assert res_thread.status_code == 200
    th_info = res_thread.json()
    tid = th_info["thread_id"]
    assert th_info["title"] == "Stripe Webhook Bugfix"
    assert th_info["group_id"] == "grp_pay"

    # 4. GET /api/groups (verify thread is embedded in group list)
    res_groups = client.get("/api/groups")
    assert res_groups.status_code == 200
    groups_list = res_groups.json()["groups"]
    assert len(groups_list) == 1
    assert groups_list[0]["group_id"] == "grp_pay"
    assert len(groups_list[0]["threads"]) == 1
    assert groups_list[0]["threads"][0]["thread_id"] == tid

    # 5. GET /api/threads/{thread_id}/messages
    res_msgs = client.get(f"/api/threads/{tid}/messages")
    assert res_msgs.status_code == 200
    assert res_msgs.json()["thread_id"] == tid
    assert isinstance(res_msgs.json()["messages"], list)

    # 6. PATCH /api/threads/{thread_id} (update title, pin, archive)
    res_patch_th = client.patch(
        f"/api/threads/{tid}",
        json={"title": "Stripe Webhook Refactored", "is_pinned": True, "is_archived": True},
    )
    assert res_patch_th.status_code == 200
    assert res_patch_th.json()["title"] == "Stripe Webhook Refactored"
    assert res_patch_th.json()["is_pinned"] is True
    assert res_patch_th.json()["is_archived"] is True

    # 7. DELETE /api/threads/{thread_id}
    res_del_th = client.delete(f"/api/threads/{tid}")
    assert res_del_th.status_code == 200
    assert res_del_th.json()["status"] == "ok"

    # Verify thread removed from group
    res_groups_after = client.get("/api/groups")
    assert len(res_groups_after.json()["groups"][0]["threads"]) == 0

    # 8. DELETE /api/groups/{group_id}
    res_del_grp = client.delete("/api/groups/grp_pay")
    assert res_del_grp.status_code == 200
    assert res_del_grp.json()["status"] == "ok"


def test_composed_group_creates_project_scoped_windows_and_registry(temp_git_repo: Path):
    """Final composition persists actual Agent windows, graph, and directed registry edges."""
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    project = client.get("/api/projects").json()["projects"][0]
    project_id = project["id"]
    body = {
        "project_id": project_id,
        "group_mode": "workflow",
        "name": "Release group",
        "goal": "Prepare a release",
        "nodes": [
            {
                "id": "lead",
                "type": "agent",
                "title": "Coordinator",
                "role": "coordinator",
                "responsibilities": ["dispatch"],
            },
            {"id": "review", "type": "agent", "title": "Reviewer", "role": "reviewer", "responsibilities": ["review"]},
            {"id": "done", "type": "output", "title": "Result"},
        ],
        "edges": [
            {"source": "lead", "target": "review", "relation": "review request"},
            {"source": "review", "target": "done", "relation": "review result"},
        ],
    }
    # The draft endpoint must not be called implicitly: before final confirmation there are no group/session files.
    agents_dir = temp_git_repo / ".agents"
    assert not list((agents_dir / "groups").glob("*.json")) if (agents_dir / "groups").exists() else True
    assert not list((agents_dir / "sessions").glob("*.json")) if (agents_dir / "sessions").exists() else True

    response = client.post("/api/groups/compose", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    group = result["group"]
    assert group["project_id"] == project_id
    assert len(result["threads"]) == 2
    assert all((agents_dir / "sessions" / f"{thread['thread_id']}.json").exists() for thread in result["threads"])

    def read_registry() -> dict:
        path = agents_dir / "registries" / f"{group['group_id']}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    registry = read_registry()
    assert len(registry["agents"]) == 2
    assert len(registry["edges"]) == 1
    assert len(client.get("/api/groups", params={"project_id": project_id}).json()["groups"]) == 1

    updated_nodes = group["nodes"]
    updated_nodes[0]["title"] = "Release coordinator"
    updated_nodes[0]["responsibilities"] = ["dispatch and summarize"]
    update_response = client.patch(
        f"/api/groups/{group['group_id']}", params={"project_id": project_id}, json={"nodes": updated_nodes}
    )
    assert update_response.status_code == 200
    updated_registry = read_registry()
    coordinator = next(
        agent for agent in updated_registry["agents"] if agent["thread_id"] == updated_nodes[0]["thread_id"]
    )
    assert coordinator["title"] == "Release coordinator"
    assert coordinator["responsibilities"] == ["dispatch and summarize"]

    added = client.post(
        f"/api/groups/{group['group_id']}/threads",
        params={"project_id": project_id},
        json={"title": "Release operator", "role": "operator", "responsibilities": "prepare release notes"},
    )
    assert added.status_code == 200
    added_thread = added.json()
    assert added_thread["metadata"]["group_goal"] == "Prepare a release"
    refreshed_group = client.get("/api/groups", params={"project_id": project_id}).json()["groups"][0]
    assert any(node.get("thread_id") == added_thread["thread_id"] for node in refreshed_group["nodes"])
    assert len(read_registry()["agents"]) == 3


def test_mcp_market_search_uses_registry_search_parameter(temp_git_repo: Path):
    """Map the UI's `q` term to the Registry's documented `search` parameter."""
    import hashlib
    import time

    from vera_agent.server.routes import mcp as mcp_routes

    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    mcp_routes._MCP_MARKET_CACHE.clear()
    cache_key = hashlib.sha256(b"github\0").hexdigest()
    stale_cache = temp_git_repo / ".agents" / "registries" / "mcp-market-cache" / f"{cache_key}.json"
    stale_cache.parent.mkdir(parents=True, exist_ok=True)
    stale_cache.write_text(
        json.dumps({"fetched_at": time.time(), "payload": {"market": [{"id": "stale"}]}}), encoding="utf-8"
    )
    requested_urls: list[str] = []

    class RegistryResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit: int) -> bytes:
            return json.dumps({"servers": [], "metadata": {}}).encode()

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return RegistryResponse()

    with patch.object(mcp_routes, "urlopen", side_effect=fake_urlopen):
        response = client.get("/api/mcp/market", params={"q": "github"})

    assert response.status_code == 200
    query = parse_qs(urlsplit(requested_urls[0]).query)
    assert query["search"] == ["github"]
    assert query["limit"] == ["10"]
    assert "q" not in query
    updated_cache = json.loads(stale_cache.read_text(encoding="utf-8"))
    assert updated_cache["version"] == mcp_routes._MCP_MARKET_CACHE_VERSION


def test_isolated_workflow_control_uses_provider_compatible_json_and_validates_shape(temp_git_repo: Path):
    app = create_app(repo_root=temp_git_repo)
    client = TestClient(app)
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    model_config = temp_git_repo / ".agents" / "models_config.json"
    model_config.parent.mkdir(parents=True, exist_ok=True)
    model_config.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "test-chat-model",
                        "name": "deepseek/deepseek-chat",
                        "provider": "deepseek",
                        "api_key": "test-only",
                        "base_url": "https://api.deepseek.com",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    group_response = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": "workflow",
            "name": "Control decision fixture",
            "goal": "Check the release result.",
            "background": "This project ships a local desktop application.",
            "nodes": [
                {
                    "id": "reviewer",
                    "type": "agent",
                    "title": "Reviewer",
                    "role": "reviewer",
                    "background": "You are a release quality specialist.",
                    "responsibilities": ["verify acceptance"],
                    "constraints": ["Do not infer missing evidence."],
                    "output_spec": "Return findings and verdict.",
                    "prompt_template": "Review the result.",
                },
                {
                    "id": "branch",
                    "type": "condition",
                    "title": "验收分支",
                    "config": {"expression": "上游结果已经通过验收"},
                },
                {
                    "id": "loop",
                    "type": "loop",
                    "title": "修改循环",
                    "config": {"continue_condition": "结果已经达到目标", "max_iterations": 4},
                },
            ],
            "edges": [{"id": "review-branch", "source": "reviewer", "target": "branch"}],
        },
    )
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()["group"]
    assert group["goal"] == "Check the release result."
    assert group["background"] == "This project ships a local desktop application."
    run_response = client.post(
        f"/api/groups/{group['group_id']}/runs",
        json={
            "project_id": project_id,
            "confirmation": "Y",
            "input": "Is the result complete?",
        },
    )
    assert run_response.status_code == 201, run_response.text
    thread_id = next(
        item["thread_id"] for item in run_response.json()["run"]["sessions"] if item["node_id"] == "branch"
    )
    observed: list[dict[str, Any]] = []

    def fake_query_stream(_model, messages, _tools=None, *, on_text, **_kwargs):
        system_content = messages[0]["content"]
        current: dict[str, Any] = {}
        current["system"] = (
            "\n".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in system_content)
            if isinstance(system_content, list)
            else str(system_content)
        )
        current["response_format"] = _kwargs.get("response_format")
        current["tools"] = _tools if _tools is not None else _kwargs.get("tools")
        observed.append(current)
        loop_schema = "feedback is required" in current["system"]
        result = (
            '{"decision":"NO","reason":"仍有一项未达到退出条件","feedback":"返回实现窗口，补齐缺失项后重新提交检查。"}'
            if loop_schema
            else '{"decision":"YES","reason":"上游结果已通过验收"}'
        )
        on_text(result)
        return {"role": "assistant", "content": result, "extra": {"actions": []}}

    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        response = client.post(
            "/api/chat/stream",
            json={
                "thread_id": thread_id,
                "project_id": project_id,
                "group_id": group["group_id"],
                "content": "Evaluate the workflow condition against the upstream result.",
                "model_id": "test-chat-model",
                "workflow_stage": "control_decision",
                "workflow_input": "Is the result complete?",
                "workflow_context": {
                    "task": "Is the result complete?",
                    "upstream": [
                        {
                            "node_id": "worker",
                            "title": "Worker",
                            "relation": "handoff",
                            "label": "verified result",
                            "output": "Completed and verified.",
                        }
                    ],
                },
                "workflow_control": {"type": "condition", "condition": "上游结果已经通过验收"},
            },
        )

    assert response.status_code == 200, response.text
    assert "decision" in response.text and "YES" in response.text
    branch_call = observed[0]
    assert "ORCHESTRATION CONTROL DECISION" in branch_call["system"]
    assert "JSON Schema" in branch_call["system"]
    assert "上游结果已经通过验收" in branch_call["system"]
    assert '"node_id": "worker"' in branch_call["system"]
    assert '"output": "Completed and verified."' in branch_call["system"]
    assert "Group goal: Check the release result." in branch_call["system"]
    assert "Project background: This project ships a local desktop application." in branch_call["system"]
    assert branch_call["tools"] == []
    assert branch_call["response_format"] == {"type": "json_object"}
    assert "required json object shape" in branch_call["system"]
    assert '"decision": "YES"' in branch_call["system"]

    loop_thread_id = next(
        item["thread_id"] for item in run_response.json()["run"]["sessions"] if item["node_id"] == "loop"
    )
    with patch.object(LitellmModel, "query_stream", new=fake_query_stream):
        loop_response = client.post(
            "/api/chat/stream",
            json={
                "thread_id": loop_thread_id,
                "project_id": project_id,
                "group_id": group["group_id"],
                "content": "Judge whether the loop can exit.",
                "model_id": "test-chat-model",
                "workflow_stage": "control_decision",
                "workflow_input": "Finish the release checklist.",
                "workflow_context": {
                    "task": "Finish the release checklist.",
                    "upstream": [
                        {
                            "node_id": "reviewer",
                            "title": "Reviewer",
                            "output": "One item is incomplete.",
                        }
                    ],
                },
                "workflow_control": {"type": "loop", "condition": "结果已经达到目标", "max_iterations": 4},
            },
        )
    assert loop_response.status_code == 200, loop_response.text
    loop_call = observed[1]
    assert "YES means the exit condition is met and exits the loop" in loop_call["system"]
    assert "NO means continue another iteration" in loop_call["system"]
    assert "feedback is required" in loop_call["system"]
    assert loop_call["response_format"] == {"type": "json_object"}
    assert '"feedback": "Concrete next action for the loop body."' in loop_call["system"]


def test_workflow_run_states_are_validated_and_persisted_atomically(temp_git_repo: Path):
    client = TestClient(create_app(repo_root=temp_git_repo))
    project_id = client.get("/api/projects").json()["projects"][0]["id"]
    group_response = client.post(
        "/api/groups/instances",
        json={
            "project_id": project_id,
            "group_mode": "workflow",
            "name": "Run state fixture",
            "nodes": [
                {"id": "source", "type": "agent", "title": "Source", "role": "source"},
                {"id": "worker", "type": "agent", "title": "Worker", "role": "worker"},
            ],
            "edges": [{"id": "source-worker", "source": "source", "target": "worker"}],
        },
    )
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()["group"]
    created = client.post(
        f"/api/groups/{group['group_id']}/runs",
        json={
            "project_id": project_id,
            "confirmation": "Y",
            "input": "Inspect the run contract.",
        },
    )
    assert created.status_code == 201, created.text
    run = created.json()["run"]
    assert [item["status"] for item in run["nodes"]] == ["pending", "pending"]
    assert run["events"][0]["type"] == "run_created"

    update_url = f"/api/groups/{group['group_id']}/runs/{run['run_id']}?project_id={project_id}"
    started = client.patch(update_url, json={"status": "running"})
    assert started.status_code == 200, started.text
    worker_running = client.patch(
        update_url,
        json={
            "nodes": [
                {"node_id": "worker", "status": "running", "output": "", "inputs": []},
            ]
        },
    )
    assert worker_running.status_code == 200, worker_running.text
    invalid_node = client.patch(
        update_url, json={"nodes": [{"node_id": "unknown", "status": "completed", "output": "x"}]}
    )
    assert invalid_node.status_code == 400
    completed = client.patch(
        update_url,
        json={
            "status": "completed",
            "final_output": "Delivered",
            "nodes": [
                {"node_id": "source", "status": "skipped", "output": "", "inputs": []},
                {
                    "node_id": "worker",
                    "status": "completed",
                    "output": "DONE",
                    "inputs": [
                        {
                            "node_id": "source",
                            "title": "Source",
                            "relation": "handoff",
                            "output": "SOURCE_DATA",
                        }
                    ],
                },
            ],
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["run"]["status"] == "completed"
    assert completed.json()["run"]["nodes"][1]["output"] == "DONE"
    assert completed.json()["run"]["nodes"][1]["inputs"][0]["output"] == "SOURCE_DATA"
    assert completed.json()["run"]["final_output"] == "Delivered"
    late_update = client.patch(update_url, json={"status": "running"})
    assert late_update.status_code == 409

    failed_run_response = client.post(
        f"/api/groups/{group['group_id']}/runs",
        json={
            "project_id": project_id,
            "confirmation": "Y",
            "input": "Exercise failure monitoring.",
        },
    )
    failed_run = failed_run_response.json()["run"]
    failed_url = f"/api/groups/{group['group_id']}/runs/{failed_run['run_id']}?project_id={project_id}"
    assert client.patch(failed_url, json={"status": "running"}).status_code == 200
    failed = client.patch(
        failed_url,
        json={
            "status": "failed",
            "error": "Worker returned an invalid response.",
            "nodes": [
                {
                    "node_id": "source",
                    "status": "failed",
                    "output": "partial output",
                    "error": "Provider timeout",
                    "inputs": [],
                },
                {"node_id": "worker", "status": "skipped", "output": "", "inputs": []},
            ],
        },
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["run"]["error"] == "Worker returned an invalid response."
    assert failed.json()["run"]["nodes"][0]["error"] == "Provider timeout"
    assert failed.json()["run"]["nodes"][1]["status"] == "skipped"

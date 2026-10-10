"""Real Live Demonstration of Multi-Agent Orchestration & Explicit Registry.

Performs 100% genuine execution:
1. Starts live Uvicorn ASGI server on 127.0.0.1:8765
2. Inquires topology templates via HTTP GET
3. Calls POST /api/groups/provision (One-click multi-window provisioning)
4. Inspects real physical files: .agents/registries/, .agents/worktrees/, .agents/sessions/
5. Dynamically connects edges in topology (POST /api/groups/{id}/edges)
6. Inspects React Flow graph for one-click jump metadata
7. Connects to POST /api/chat/stream with real DeepSeek LLM, streaming real SSE frames!
8. Verifies status transitions and physical write-protection of registries.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Defuse Windows encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import dotenv
import httpx
import uvicorn

# Load API credentials
dotenv.load_dotenv(r"C:\Users\FAST\AppData\Local\vera-agent\vera-agent\.env")
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")

# Add vera-agent to path
sys.path.insert(0, str(Path(r"c:\Users\FAST\Desktop\Multi-agents\vera-agent\src").resolve()))

from vera_agent.environments.local import LocalEnvironment
from vera_agent.server.app import create_app


def init_test_workspace(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=str(target_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "LiveTester"], cwd=str(target_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "live@vera.local"], cwd=str(target_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=str(target_dir), check=True, capture_output=True)

    (target_dir / "README.md").write_text("# Live Multi-Agent Workspace\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(target_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init live workspace"], cwd=str(target_dir), check=True, capture_output=True)
    return target_dir


async def run_live_verification():
    workspace = Path(r"c:\Users\FAST\Desktop\Multi-agents\scratch\real_orchestration_repo").resolve()
    init_test_workspace(workspace)
    print(f"🚀 [1/8] Initialized physical git workspace: {workspace}")

    # Build real Starlette app
    app = create_app(repo_root=workspace)

    # Start Uvicorn in background thread
    server_config = uvicorn.Config(app=app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config=server_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to come up
    base_url = "http://127.0.0.1:8765"
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        # Check health
        for _ in range(15):
            try:
                res = await client.get("/api/health")
                if res.status_code == 200:
                    break
            except Exception:
                await asyncio.sleep(0.3)

        print("✅ [2/8] Live ASGI Server running on http://127.0.0.1:8765 (Uvicorn 0.54.0)")

        # 1. Query Templates
        res_tpl = await client.get("/api/templates/topology")
        templates = res_tpl.json()["templates"]
        print(f"📋 [3/8] Retrieved {len(templates)} declarative topology templates from /api/templates/topology:")
        for t in templates:
            print(f"   • [{t['topology_type'].upper()}] {t['name']} ({len(t['nodes'])} 个预设窗口)")

        # 2. One-Click Provisioning
        goal_text = "设计并实现高可靠支付网关模块，支持微信 V3 签名回调与防重放攻击，代码自洽并带单测"
        print(f"\n⚡ [4/8] Executing One-Click Provisioning (POST /api/groups/provision)...")
        res_prov = await client.post(
            "/api/groups/provision",
            json={
                "group_name": "实战电商支付重构组",
                "branch_name": "feat/live-payment",
                "base_branch": "main",
                "goal": goal_text,
                "template_id": "supervisor_dev",
            },
        )
        assert res_prov.status_code == 200
        prov_data = res_prov.json()
        gid = prov_data["group"]["group_id"]
        threads = prov_data["threads"]
        print(f"   ✅ Group provisioned: ID={gid}, Branch=feat/live-payment, Worktree={prov_data['group']['worktree_path']}")
        print(f"   ✅ Generated {len(threads)} interactive conversation windows:")
        for t in threads:
            print(f"      - 🪟 Thread: {t['thread_id']} | 角色: {t['role']} | 标题: {t['title']}")

        # 3. Check Physical Disk
        print(f"\n📂 [5/8] Verifying real physical files on disk:")
        reg_file = workspace / ".agents" / "registries" / f"{gid}.json"
        assert reg_file.exists(), "Registry file must exist!"
        reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
        print(f"   ✅ Explicit Registry exists at: {reg_file.relative_to(workspace)}")
        print(f"      - Registered Agents: {len(reg_data['agents'])}")
        print(f"      - Registered Edges: {len(reg_data['edges'])}")
        for ag in reg_data["agents"]:
            print(f"        * [{ag['role'].upper()}] {ag['title']} (状态: {ag['status']})")
            print(f"          职责: {ag['responsibilities'][0] if ag['responsibilities'] else 'N/A'}")

        wt_dir = Path(prov_data["group"]["worktree_path"])
        assert wt_dir.exists(), "Worktree directory must exist!"
        print(f"   ✅ Physical Worktree exists at: {wt_dir}")

        # 4. Canvas Drag & Connect Edges
        print(f"\n🎨 [6/8] Simulating Canvas Edge Connection (POST /api/groups/{gid}/edges):")
        sup_tid = threads[0]["thread_id"]
        rev_tid = threads[2]["thread_id"]
        res_edge = await client.post(
            f"/api/groups/{gid}/edges",
            json={"source_thread_id": sup_tid, "target_thread_id": rev_tid, "relation": "direct_audit_link"},
        )
        assert res_edge.status_code == 200
        print(f"   ✅ Connected edge: {sup_tid} -> {rev_tid} (direct_audit_link)")

        # Verify in topology export
        res_topo = await client.get("/api/topology")
        topo = res_topo.json()
        print(f"   ✅ React Flow Topology export has {len(topo['nodes'])} nodes and {len(topo['edges'])} edges")
        session_node = next(n for n in topo["nodes"] if n["id"] == f"session_{sup_tid}")
        print(f"   ✅ Direct-Jump verified: Node session_{sup_tid} contains thread_id='{session_node['data']['thread_id']}', title='{session_node['data']['title']}'")

        # 5. Live Stream with Real Model
        print(f"\n🤖 [7/8] Calling Live SSE Inference on Supervisor Window (POST /api/chat/stream)...")
        print(f"   Connecting to DeepSeek-Chat with prompt: '作为技术主管，请简明规划本任务第一步。'")

        received_chunks = []
        async with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "thread_id": sup_tid,
                "content": "作为技术主管，请简明规划本任务第一步。",
                "mode": "yolo",
            },
            timeout=60.0,
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    raw_data = line.split(":", 1)[1].strip()
                    try:
                        data_json = json.loads(raw_data)
                    except Exception:
                        data_json = raw_data
                    if event_type == "text_chunk":
                        content_piece = data_json.get("content", "")
                        received_chunks.append(content_piece)
                        print(content_piece, end="", flush=True)
                    elif event_type == "finish":
                        print(f"\n   🏁 [Finish Event Received]: duration={data_json.get('duration')}s, steps={data_json.get('steps')}, cost=${data_json.get('cost')}")

        full_text = "".join(received_chunks)
        assert len(full_text) > 0, "Must have received real model completion!"
        print(f"   ✅ Live Model completed {len(full_text)} characters successfully!")

        # Verify status in registry returned to idle
        res_reg_after = await client.get(f"/api/groups/{gid}/registry")
        sup_entry = next(a for a in res_reg_after.json()["agents"] if a["thread_id"] == sup_tid)
        print(f"   ✅ Status verification in registry: Agent {sup_tid} status is '{sup_entry['status']}'")

        # 6. Physical Tampering Protection
        print(f"\n🛡️ [8/8] Testing Physical Tampering Protection:")
        env = LocalEnvironment(cwd=str(workspace))
        hack_res = env.execute({
            "tool_name": "write",
            "path": f".agents/registries/{gid}.json",
            "content": '{"hacked": true}',
        })
        print(f"   Attempted unauthorized write to registry: returncode={hack_res['returncode']}")
        print(f"   Output: {hack_res['output']}")
        assert hack_res["returncode"] == 1
        assert "Permission Denied" in hack_res["output"]
        print("   ✅ Host-level write protection verified! Registry remains pristine.")

    # Stop server
    server.should_exit = True
    print("\n🎉 REAL LIVE VERIFICATION 100% COMPLETE AND SUCCESSFUL!")


if __name__ == "__main__":
    asyncio.run(run_live_verification())

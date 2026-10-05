"""Real-world end-to-end integration test covering all multi-agent features."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest

from vera_agent.models.contracts import HandoverPayload
from vera_agent.session.graph import GitFlowGraph
from vera_agent.session.router import SessionRouter
from vera_agent.session.worktree import WorktreeManager


def run_git(args: list[str], cwd: Path) -> str:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return proc.stdout.strip()


@pytest.mark.asyncio
async def test_real_scenario_e2e():
    """Execute complete 10-step production scenario."""
    temp_dir = Path(tempfile.mkdtemp(prefix="agent_real_scenario_"))
    try:
        repo_root = temp_dir / "ecommerce_core"
        repo_root.mkdir(parents=True, exist_ok=True)

        # 1. Base repo
        run_git(["init", "-b", "main"], repo_root)
        run_git(["config", "user.name", "ProductionAgent"], repo_root)
        run_git(["config", "user.email", "agent@prod.local"], repo_root)
        run_git(["config", "commit.gpgsign", "false"], repo_root)

        (repo_root / "order_service.py").write_text(
            "class OrderService:\n"
            "    def create_order(self, item_id: str, quantity: int) -> dict:\n"
            "        return {'status': 'created', 'item': item_id, 'qty': quantity}\n",
            encoding="utf-8",
        )
        (repo_root / "config.py").write_text(
            "APP_NAME = 'ECommerceCore'\nDATABASE_PORT = 5432\n",
            encoding="utf-8",
        )
        run_git(["add", "."], repo_root)
        run_git(["commit", "-m", "chore: initial core service"], repo_root)

        # 2. Provision worktrees
        wt_manager = WorktreeManager(repo_root=repo_root)
        graph = GitFlowGraph(repo_root=repo_root, worktree_manager=wt_manager)
        router = SessionRouter(graph=graph)

        grp_payment = graph.create_group(
            group_id="grp_payment",
            branch_name="feat/stripe-payment",
            base_branch="main",
            name="Payment Services Team",
        )
        grp_inventory = graph.create_group(
            group_id="grp_inventory",
            branch_name="feat/redis-inventory",
            base_branch="main",
            name="Inventory Services Team",
        )
        assert (grp_payment.worktree_path / "order_service.py").exists()

        # 3. Register sessions
        graph.register_session("th_pay_lead", role="implementer", group_id="grp_payment")
        graph.register_session("th_pay_reviewer", role="reviewer", group_id="grp_payment")
        graph.register_session("th_inv_lead", role="implementer", group_id="grp_inventory")

        # 4. Feature execution & Checkpoint
        pay_file = grp_payment.worktree_path / "payment_gateway.py"
        pay_file.write_text("class StripeGateway: pass\n", encoding="utf-8")
        assert wt_manager.get_worktree_status(grp_payment.worktree_path)["is_dirty"]

        cp_hash = wt_manager.create_checkpoint(grp_payment.worktree_path, "feat: StripeGateway")
        assert cp_hash
        assert not wt_manager.get_worktree_status(grp_payment.worktree_path)["is_dirty"]

        # 5. Disaster recovery
        pay_file.write_text("BROKEN SYNTAX ERROR", encoding="utf-8")
        assert wt_manager.get_worktree_status(grp_payment.worktree_path)["is_dirty"]
        wt_manager.reset_worktree(grp_payment.worktree_path, hard=True)
        assert not wt_manager.get_worktree_status(grp_payment.worktree_path)["is_dirty"]
        assert "class StripeGateway:" in pay_file.read_text(encoding="utf-8")

        # 6. Hot-plug rescue session
        graph.register_session("th_rescuer", role="rescue_lead")
        attached = graph.attach_session_to_group("th_rescuer", "grp_payment")
        assert attached
        assert graph.sessions["th_rescuer"]["attached_worktree"] == str(grp_payment.worktree_path)

        # 7. Physical isolation check
        (grp_inventory.worktree_path / "cache.py").write_text("class RedisCache: pass\n", encoding="utf-8")
        wt_manager.create_checkpoint(grp_inventory.worktree_path, "feat: RedisCache")
        assert not (grp_payment.worktree_path / "cache.py").exists()

        # 8. Async Handover
        handover = HandoverPayload(
            source_thread_id="th_pay_lead",
            role="implementer",
            target_problem="Integrate Stripe",
            touched_files=["payment_gateway.py"],
            key_findings=["TLS 1.3 required"],
            rejected_paths=["Do not use raw SQL"],
            next_action="Run test suite",
        )
        await router.send_handover("th_pay_lead", "th_pay_reviewer", handover)
        rec = await router.receive_message("th_pay_reviewer", timeout=1.0)
        assert rec is not None
        assert rec.payload["rejected_paths"] == ["Do not use raw SQL"]

        # 9. In-memory Merge Review
        clean_review = await router.request_merge_review(
            "feat/stripe-payment", "main", "th_pay_lead", "th_pay_reviewer"
        )
        assert clean_review.can_merge is True

        # Conflict check
        (grp_payment.worktree_path / "config.py").write_text("PORT = 9999\n", encoding="utf-8")
        wt_manager.create_checkpoint(grp_payment.worktree_path, "port 9999")
        (grp_inventory.worktree_path / "config.py").write_text("PORT = 7777\n", encoding="utf-8")
        wt_manager.create_checkpoint(grp_inventory.worktree_path, "port 7777")

        conflict_review = await router.request_merge_review(
            "feat/stripe-payment", "feat/redis-inventory", "th_pay_lead", "th_inv_lead"
        )
        assert conflict_review.can_merge is False
        assert len(conflict_review.conflict_files) > 0

        # 10. React Flow Topology
        topo = graph.export_topology("e2e_topology")
        data = topo.model_dump()
        assert len(data["nodes"]) >= 8
        assert len(data["edges"]) >= 8

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

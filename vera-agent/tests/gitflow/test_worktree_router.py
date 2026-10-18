"""Handoff contracts, Git worktree management, GitFlowGraph, and SessionRouter messaging."""

import os
import subprocess
from pathlib import Path

import pytest

from vera_agent.models.contracts import (
    AgentDeps,
    GraphTopology,
    HandoverPayload,
    MergeReviewResult,
)
from vera_agent.session.graph import GitFlowGraph
from vera_agent.session.router import (
    SessionMessage,
    SessionRouter,
    prompt_structured_choice,
)
from vera_agent.session.worktree import WorktreeManager


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Initialize a real temporary git repository for testing Worktree operations."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    def run_git(args, cwd=repo_dir):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    run_git(["init", "-b", "main"])
    run_git(["config", "user.name", "TestAgent"])
    run_git(["config", "user.email", "agent@test.local"])
    run_git(["config", "commit.gpgsign", "false"])

    # Initial commit
    init_file = repo_dir / "README.md"
    init_file.write_text("# Test Repo\n", encoding="utf-8")
    run_git(["add", "README.md"])
    run_git(["commit", "-m", "Initial commit"])

    return repo_dir


# ==========================================
# 1. Typed Contracts Tests
# ==========================================


def test_agent_deps_container():
    deps = AgentDeps(
        env="dummy_env",
        session="dummy_session",
        worktree_path=Path("/tmp/wt"),
        scratch_dir=Path("/tmp/scratch"),
        group_id="group_01",
    )
    assert deps.env == "dummy_env"
    assert deps.group_id == "group_01"
    assert deps.worktree_path == Path("/tmp/wt")


def test_handover_payload_validation_and_markdown():
    payload = HandoverPayload(
        source_thread_id="th_research_01",
        role="researcher",
        target_problem="Fix zero division in math module",
        touched_files=["math/calc.py"],
        key_findings=["Missing denominator check at line 42", "Unit tests exist in tests/test_calc.py"],
        rejected_paths=["Using try-except globally (breaks existing ValueError contracts)"],
        next_action="Add explicit zero check before division",
    )

    md = payload.to_markdown()
    assert "Context Handover [RESEARCHER -> Next]" in md
    assert "Missing denominator check at line 42" in md
    assert "❌ Using try-except globally" in md
    assert "Add explicit zero check before division" in md
    assert "math/calc.py" in md


def test_merge_review_result_markdown():
    res_pass = MergeReviewResult(
        source_branch="feat/calc",
        target_branch="main",
        can_merge=True,
        diff_summary="1 file changed, 2 insertions(+)",
        test_passed=True,
    )
    md_pass = res_pass.to_markdown()
    assert "✅ CAN MERGE" in md_pass
    assert "No merge conflicts detected" in md_pass

    res_block = MergeReviewResult(
        source_branch="feat/broken",
        target_branch="main",
        can_merge=False,
        conflict_files=["math/calc.py"],
        test_passed=False,
        action_items=["Fix conflict in math/calc.py"],
    )
    md_block = res_block.to_markdown()
    assert "`[CONFLICT]` math/calc.py" in md_block
    assert "- [ ] Fix conflict in math/calc.py" in md_block


# ==========================================
# 2. Git Worktree Lifecycle Tests
# ==========================================


def test_worktree_lifecycle_and_checkpoints(temp_git_repo: Path):
    wt_manager = WorktreeManager(repo_root=temp_git_repo)

    # 1. Create worktree
    wt_path = wt_manager.create_worktree(branch="feat/login", base_branch="main")
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()

    # 2. List worktrees
    worktrees = wt_manager.list_worktrees()
    assert len(worktrees) == 2
    branches = [w.get("branch") for w in worktrees]
    assert "main" in branches
    assert "feat/login" in branches

    # 3. Check clean status
    status = wt_manager.get_worktree_status(wt_path)
    assert not status["is_dirty"]
    assert len(status["dirty_files"]) == 0

    # 4. Modify file & create checkpoint commit
    auth_file = wt_path / "auth.py"
    auth_file.write_text("def login(): return True\n", encoding="utf-8")
    status_dirty = wt_manager.get_worktree_status(wt_path)
    assert status_dirty["is_dirty"]
    assert len(status_dirty["dirty_files"]) == 1

    commit_hash = wt_manager.create_checkpoint(wt_path, message="Add auth module")
    assert commit_hash

    # Now status should be clean
    status_after_cp = wt_manager.get_worktree_status(wt_path)
    assert not status_after_cp["is_dirty"]

    # 5. Make another dirty edit and test reset_worktree
    auth_file.write_text("broken syntax !!!", encoding="utf-8")
    assert wt_manager.get_worktree_status(wt_path)["is_dirty"]

    reset_ok = wt_manager.reset_worktree(wt_path, hard=True)
    assert reset_ok
    assert not wt_manager.get_worktree_status(wt_path)["is_dirty"]
    assert auth_file.read_text(encoding="utf-8") == "def login(): return True\n"

    # 6. Test diff against main
    diff = wt_manager.get_diff(wt_path, base_branch="main")
    assert "def login(): return True" in diff

    # 7. Remove worktree
    removed = wt_manager.remove_worktree(branch="feat/login", force=True)
    assert removed
    assert not wt_path.exists()


def test_worktree_try_merge_in_memory(temp_git_repo: Path):
    wt_manager = WorktreeManager(repo_root=temp_git_repo)

    # Create branch A modifying a.txt
    wt_a = wt_manager.create_worktree(branch="feat/a", base_branch="main")
    (wt_a / "a.txt").write_text("file A content\n", encoding="utf-8")
    wt_manager.create_checkpoint(wt_a, "add a.txt")

    # Create branch B modifying b.txt
    wt_b = wt_manager.create_worktree(branch="feat/b", base_branch="main")
    (wt_b / "b.txt").write_text("file B content\n", encoding="utf-8")
    wt_manager.create_checkpoint(wt_b, "add b.txt")

    # Try merge feat/a into main -> Should succeed
    can_merge, conflicts, _ = wt_manager.try_merge("feat/a", "main")
    assert can_merge
    assert len(conflicts) == 0

    # Cleanup worktrees
    wt_manager.remove_worktree("feat/a", force=True)
    wt_manager.remove_worktree("feat/b", force=True)


# ==========================================
# 3. GitFlowGraph & React Flow Topology Tests
# ==========================================


def test_gitflow_graph_and_topology_export(temp_git_repo: Path):
    graph = GitFlowGraph(repo_root=temp_git_repo)

    # 1. Create ProjectGroup
    group = graph.create_group(
        group_id="grp_pay",
        branch_name="feat/payment",
        base_branch="main",
        name="Payment Dev Group",
    )
    assert group.group_id == "grp_pay"
    assert group.worktree_path.exists()

    # 2. Register Sessions
    graph.register_session(
        thread_id="th_impl_01",
        role="implementer",
        group_id="grp_pay",
        status="active",
    )
    graph.register_session(
        thread_id="th_review_01",
        role="reviewer",
        group_id="grp_pay",
        status="idle",
    )

    # 3. Test hot-plug detach and re-attach
    detached = graph.detach_session("th_review_01")
    assert detached
    assert graph.sessions["th_review_01"]["group_id"] is None

    attached = graph.attach_session_to_group("th_review_01", "grp_pay")
    assert attached
    assert graph.sessions["th_review_01"]["group_id"] == "grp_pay"

    # 4. Record communication
    graph.record_communication("th_impl_01", "th_review_01", label="handover")

    # 5. Export topology for Web Frontend
    topology = graph.export_topology(graph_id="test_topology")
    assert isinstance(topology, GraphTopology)
    assert len(topology.nodes) >= 3  # branch, worktree, session
    assert len(topology.edges) >= 2

    # Check React Flow serialization
    data_dict = topology.model_dump()
    assert "nodes" in data_dict
    assert "edges" in data_dict
    node_types = {n["type"] for n in data_dict["nodes"]}
    assert "branchNode" in node_types
    assert "worktreeNode" in node_types
    assert "sessionNode" in node_types

    # Cleanup
    graph.worktree_manager.remove_worktree("feat/payment", force=True)


# ==========================================
# 4. SessionRouter Async Bus Tests
# ==========================================


@pytest.mark.asyncio
async def test_session_router_async_communication(temp_git_repo: Path):
    graph = GitFlowGraph(repo_root=temp_git_repo)
    router = SessionRouter(graph=graph)

    # Register 2 sessions
    graph.register_session(thread_id="th_sender", role="implementer")
    graph.register_session(thread_id="th_receiver", role="reviewer")

    # 1. Send point-to-point text message
    msg = await router.send_message(
        source_thread_id="th_sender",
        target_thread_id="th_receiver",
        content="Ready for review",
    )
    assert isinstance(msg, SessionMessage)
    assert msg.content == "Ready for review"

    # 2. Receive message
    rec_msg = await router.receive_message("th_receiver", timeout=1.0)
    assert rec_msg is not None
    assert rec_msg.content == "Ready for review"

    # Queue should now be empty
    empty_check = await router.receive_message("th_receiver", timeout=0.1)
    assert empty_check is None

    # 3. Send structured HandoverPayload
    handover = HandoverPayload(
        source_thread_id="th_sender",
        role="implementer",
        target_problem="Add validation",
        touched_files=["val.py"],
        key_findings=["Validated regex"],
        next_action="Verify edge cases",
    )
    handover_msg = await router.send_handover("th_sender", "th_receiver", handover)
    assert handover_msg.message_type == "handover"
    assert handover_msg.payload["target_problem"] == "Add validation"

    rec_handover = await router.receive_message("th_receiver", timeout=1.0)
    assert rec_handover is not None
    assert rec_handover.payload["touched_files"] == ["val.py"]


@pytest.mark.asyncio
async def test_session_router_broadcast_and_merge_request(temp_git_repo: Path):
    graph = GitFlowGraph(repo_root=temp_git_repo)
    router = SessionRouter(graph=graph)

    # Create Group with 2 sessions
    graph.create_group("grp_test", branch_name="feat/test", base_branch="main")
    graph.register_session("th_1", group_id="grp_test")
    graph.register_session("th_2", group_id="grp_test")

    # Broadcast
    broadcast_msgs = await router.broadcast_to_group(
        source_thread_id="th_1",
        group_id="grp_test",
        content="Group sync event",
    )
    assert len(broadcast_msgs) == 1
    assert broadcast_msgs[0].target_thread_id == "th_2"

    rec_broadcast = await router.receive_message("th_2", timeout=1.0)
    assert rec_broadcast is not None
    assert rec_broadcast.content == "Group sync event"

    # Test merge review request
    review_res = await router.request_merge_review(
        source_branch="feat/test",
        target_branch="main",
        requester_thread_id="th_1",
        reviewer_thread_id="th_2",
    )
    assert isinstance(review_res, MergeReviewResult)
    assert review_res.source_branch == "feat/test"
    assert review_res.can_merge is True

    # Reviewer should receive merge_request message
    merge_msg = await router.receive_message("th_2", timeout=1.0)
    assert merge_msg is not None
    assert merge_msg.message_type == "merge_request"

    # Cleanup
    graph.worktree_manager.remove_worktree("feat/test", force=True)


def test_prompt_structured_choice():
    # Auto approve
    assert prompt_structured_choice("Delete branch?", auto_approve=True) == "Y"

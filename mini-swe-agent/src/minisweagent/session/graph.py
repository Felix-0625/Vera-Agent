"""GitFlow dynamic graph state model and ProjectGroup management.

Adheres to Pi-agent minimalism and provides React Flow-compatible topology:
- ProjectGroup: Workgroup tied to a specific Git branch/worktree.
- GitFlowGraph: Topology state machine tracking branches, worktrees, and sessions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from minisweagent.models.contracts import GraphEdge, GraphNode, GraphTopology
from minisweagent.session.worktree import WorktreeManager

logger = logging.getLogger(__name__)


@dataclass
class ProjectGroup:
    """Logical workgroup mapped to an isolated Git Worktree and branch."""

    group_id: str
    name: str
    branch_name: str
    worktree_path: Path
    thread_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def add_thread(self, thread_id: str) -> None:
        if thread_id not in self.thread_ids:
            self.thread_ids.append(thread_id)

    def remove_thread(self, thread_id: str) -> bool:
        if thread_id in self.thread_ids:
            self.thread_ids.remove(thread_id)
            return True
        return False

    def has_thread(self, thread_id: str) -> bool:
        return thread_id in self.thread_ids


class GitFlowGraph:
    """Dynamic graph topology state machine for multi-agent GitFlow orchestration."""

    def __init__(self, repo_root: Path | str, worktree_manager: WorktreeManager | None = None):
        self.repo_root = Path(repo_root).resolve()
        self.worktree_manager = worktree_manager or WorktreeManager(self.repo_root)
        self.groups: dict[str, ProjectGroup] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.communication_links: list[tuple[str, str, str]] = []  # (from_id, to_id, label)

    def create_group(
        self,
        group_id: str,
        branch_name: str,
        base_branch: str = "main",
        name: str | None = None,
    ) -> ProjectGroup:
        """Create or register a ProjectGroup backed by an isolated Git Worktree."""
        if group_id in self.groups:
            return self.groups[group_id]

        wt_path = self.worktree_manager.create_worktree(branch_name, base_branch=base_branch)
        group = ProjectGroup(
            group_id=group_id,
            name=name or f"Group: {branch_name}",
            branch_name=branch_name,
            worktree_path=wt_path,
        )
        self.groups[group_id] = group
        return group

    def get_group(self, group_id: str) -> ProjectGroup | None:
        return self.groups.get(group_id)

    def register_session(
        self,
        thread_id: str,
        role: str = "implementer",
        group_id: str | None = None,
        status: str = "idle",
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register or update an agent session node in the graph."""
        attached_wt = None
        if group_id and group_id in self.groups:
            group = self.groups[group_id]
            group.add_thread(thread_id)
            attached_wt = str(group.worktree_path)

        session_info = {
            "thread_id": thread_id,
            "role": role,
            "group_id": group_id,
            "status": status,
            "attached_worktree": attached_wt,
            "metrics": metrics or {},
            "updated_at": time.time(),
        }
        self.sessions[thread_id] = session_info
        return session_info

    def attach_session_to_group(self, thread_id: str, group_id: str) -> bool:
        """Hot-plug attach an agent session to a different ProjectGroup/Worktree."""
        if group_id not in self.groups or thread_id not in self.sessions:
            return False

        # Detach from previous group if any
        prev_group_id = self.sessions[thread_id].get("group_id")
        if prev_group_id and prev_group_id in self.groups:
            self.groups[prev_group_id].remove_thread(thread_id)

        target_group = self.groups[group_id]
        target_group.add_thread(thread_id)
        self.sessions[thread_id]["group_id"] = group_id
        self.sessions[thread_id]["attached_worktree"] = str(target_group.worktree_path)
        self.sessions[thread_id]["updated_at"] = time.time()
        return True

    def detach_session(self, thread_id: str) -> bool:
        """Detach an agent session from its current worktree."""
        if thread_id not in self.sessions:
            return False

        group_id = self.sessions[thread_id].get("group_id")
        if group_id and group_id in self.groups:
            self.groups[group_id].remove_thread(thread_id)

        self.sessions[thread_id]["group_id"] = None
        self.sessions[thread_id]["attached_worktree"] = None
        self.sessions[thread_id]["updated_at"] = time.time()
        return True

    def record_communication(self, from_thread: str, to_thread: str, label: str = "message") -> None:
        """Record an active communication edge between two sessions."""
        link = (from_thread, to_thread, label)
        if link not in self.communication_links:
            self.communication_links.append(link)

    def export_topology(self, graph_id: str = "gitflow_graph") -> GraphTopology:
        """Generate a complete React Flow-compatible topology for frontend visualization."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # 1. Branch nodes
        branches = set()
        for group in self.groups.values():
            branches.add(group.branch_name)

        sorted_branches = sorted(branches)
        branch_x_spacing = 260.0
        for i, branch in enumerate(sorted_branches):
            b_id = f"br_{branch.replace('/', '_')}"
            nodes.append(
                GraphNode(
                    id=b_id,
                    type="branchNode",
                    data={"name": branch, "is_main": branch in ("main", "master", "dev")},
                    position={"x": 50.0 + i * branch_x_spacing, "y": 50.0},
                )
            )

        # 2. Worktree nodes
        for i, group in enumerate(self.groups.values()):
            wt_id = f"wt_{group.group_id}"
            b_id = f"br_{group.branch_name.replace('/', '_')}"

            # Query real status from worktree_manager
            status = self.worktree_manager.get_worktree_status(group.worktree_path)
            nodes.append(
                GraphNode(
                    id=wt_id,
                    type="worktreeNode",
                    data={
                        "group_id": group.group_id,
                        "name": group.name,
                        "branch": group.branch_name,
                        "path": str(group.worktree_path),
                        "is_dirty": status.get("is_dirty", False),
                        "dirty_files_count": len(status.get("dirty_files", [])),
                        "head_commit": status.get("head_commit", ""),
                    },
                    position={"x": 50.0 + i * branch_x_spacing, "y": 200.0},
                )
            )

            # Edge: branch -> worktree
            edges.append(
                GraphEdge(
                    id=f"e_{b_id}_{wt_id}",
                    source=b_id,
                    target=wt_id,
                    label="checked_out",
                )
            )

        # 3. Session nodes
        session_x_spacing = 200.0
        for j, (thread_id, s_info) in enumerate(self.sessions.items()):
            s_id = f"session_{thread_id}"
            nodes.append(
                GraphNode(
                    id=s_id,
                    type="sessionNode",
                    data=s_info,
                    position={"x": 50.0 + j * session_x_spacing, "y": 360.0},
                )
            )

            # Edge: session -> worktree (attached)
            group_id = s_info.get("group_id")
            if group_id:
                wt_id = f"wt_{group_id}"
                edges.append(
                    GraphEdge(
                        id=f"e_{s_id}_{wt_id}",
                        source=s_id,
                        target=wt_id,
                        label="attached",
                        animated=(s_info.get("status") == "active"),
                    )
                )

        # 4. Inter-session communication edges
        for from_t, to_t, label in self.communication_links:
            s_from = f"session_{from_t}"
            s_to = f"session_{to_t}"
            edges.append(
                GraphEdge(
                    id=f"e_comm_{from_t}_{to_t}",
                    source=s_from,
                    target=s_to,
                    label=label,
                    animated=True,
                )
            )

        return GraphTopology(graph_id=graph_id, nodes=nodes, edges=edges)

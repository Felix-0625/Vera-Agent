"""Program-managed explicit agent registry service.

Ensures Ground Truth:
- Exclusively maintained by the host system engine, never directly modified by agents.
- Stores explicit roles, responsibilities, thread IDs, log URIs, and inter-window edges.
- Persisted physically in `.agents/registries/{group_id}.json`.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentRegistryEntry(BaseModel):
    """Explicit descriptor of a provisioned agent window."""

    thread_id: str
    title: str
    role: str
    responsibilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    status: str = "idle"  # idle | running | waiting_approval | finished | error
    log_uri: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class RegistryEdge(BaseModel):
    """Directed connection edge between two agent windows."""

    source_thread_id: str
    target_thread_id: str
    relation: str = "connected_to"


class GroupRegistry(BaseModel):
    """Full architectural registry for a ProjectGroup."""

    group_id: str
    group_name: str
    topology_type: str = "custom"
    goal: str = ""
    branch_name: str
    worktree_path: str
    project_id: str | None = None
    group_mode: str = "team"
    template_id: str | None = None
    workflow_nodes: list[dict[str, Any]] = Field(default_factory=list)
    workflow_edges: list[dict[str, Any]] = Field(default_factory=list)
    layout: dict[str, Any] = Field(default_factory=dict)
    agents: list[AgentRegistryEntry] = Field(default_factory=list)
    edges: list[RegistryEdge] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class RegistryManager:
    """System-level manager maintaining physical registries in `.agents/registries/`."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.registries_dir = self.repo_root / ".agents" / "registries"
        self.registries_dir.mkdir(parents=True, exist_ok=True)

    def _get_group_file(self, group_id: str) -> Path:
        return self.registries_dir / f"{group_id}.json"

    def get_group_registry(self, group_id: str) -> GroupRegistry | None:
        """Load and return group registry from disk."""
        target_file = self._get_group_file(group_id)
        if not target_file.exists():
            return None
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
            return GroupRegistry(**data)
        except Exception as e:
            logger.warning("Failed to parse registry for %s: %s", group_id, e)
            return None

    def save_group_registry(self, registry: GroupRegistry) -> None:
        """Persist group registry to disk atomically."""
        registry.updated_at = time.time()
        target_file = self._get_group_file(registry.group_id)
        target_file.write_text(
            json.dumps(registry.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_or_update_group(
        self,
        group_id: str,
        group_name: str,
        branch_name: str,
        worktree_path: str,
        topology_type: str = "custom",
        goal: str = "",
        agents: list[AgentRegistryEntry] | None = None,
        edges: list[RegistryEdge] | None = None,
    ) -> GroupRegistry:
        """Create or update full group registry descriptor."""
        existing = self.get_group_registry(group_id)
        if existing:
            existing.group_name = group_name
            existing.branch_name = branch_name
            existing.worktree_path = worktree_path
            existing.topology_type = topology_type
            if goal:
                existing.goal = goal
            if agents is not None:
                existing.agents = agents
            if edges is not None:
                existing.edges = edges
            self.save_group_registry(existing)
            return existing

        reg = GroupRegistry(
            group_id=group_id,
            group_name=group_name,
            topology_type=topology_type,
            goal=goal,
            branch_name=branch_name,
            worktree_path=worktree_path,
            agents=agents or [],
            edges=edges or [],
        )
        self.save_group_registry(reg)
        return reg

    def register_agent(
        self,
        group_id: str,
        thread_id: str,
        title: str,
        role: str,
        responsibilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        log_uri: str = "",
        status: str = "idle",
    ) -> AgentRegistryEntry:
        """Register or update an agent window within group registry."""
        reg = self.get_group_registry(group_id)
        if not reg:
            reg = GroupRegistry(
                group_id=group_id,
                group_name=group_id,
                branch_name="main",
                worktree_path=str(self.repo_root),
            )

        entry = None
        for a in reg.agents:
            if a.thread_id == thread_id:
                a.title = title
                a.role = role
                if responsibilities is not None:
                    a.responsibilities = responsibilities
                if allowed_tools is not None:
                    a.allowed_tools = allowed_tools
                a.log_uri = log_uri or a.log_uri
                a.status = status
                a.updated_at = time.time()
                entry = a
                break

        if not entry:
            entry = AgentRegistryEntry(
                thread_id=thread_id,
                title=title,
                role=role,
                responsibilities=responsibilities or [],
                allowed_tools=allowed_tools or [],
                log_uri=log_uri or f".agents/sessions/{thread_id}.json",
                status=status,
            )
            reg.agents.append(entry)

        self.save_group_registry(reg)
        return entry

    def update_agent_status(self, group_id: str, thread_id: str, status: str) -> bool:
        """Update active execution status of an agent window."""
        reg = self.get_group_registry(group_id)
        if not reg:
            return False
        for a in reg.agents:
            if a.thread_id == thread_id:
                a.status = status
                a.updated_at = time.time()
                self.save_group_registry(reg)
                return True
        return False

    def add_edge(
        self,
        group_id: str,
        source_thread_id: str,
        target_thread_id: str,
        relation: str = "connected_to",
    ) -> bool:
        """Add a directed coordination edge between two agent windows."""
        reg = self.get_group_registry(group_id)
        if not reg:
            return False

        # Check existing edge
        for e in reg.edges:
            if e.source_thread_id == source_thread_id and e.target_thread_id == target_thread_id:
                e.relation = relation
                self.save_group_registry(reg)
                return True

        reg.edges.append(
            RegistryEdge(
                source_thread_id=source_thread_id,
                target_thread_id=target_thread_id,
                relation=relation,
            )
        )
        self.save_group_registry(reg)
        return True

    def remove_edge(self, group_id: str, source_thread_id: str, target_thread_id: str) -> bool:
        """Remove a directed edge between two agent windows."""
        reg = self.get_group_registry(group_id)
        if not reg:
            return False

        original_count = len(reg.edges)
        reg.edges = [
            e
            for e in reg.edges
            if not (e.source_thread_id == source_thread_id and e.target_thread_id == target_thread_id)
        ]
        if len(reg.edges) != original_count:
            self.save_group_registry(reg)
            return True
        return False

    def remove_agent(self, group_id: str, thread_id: str) -> bool:
        """Remove an agent window and its connected edges from registry."""
        reg = self.get_group_registry(group_id)
        if not reg:
            return False

        reg.agents = [a for a in reg.agents if a.thread_id != thread_id]
        reg.edges = [
            e
            for e in reg.edges
            if e.source_thread_id != thread_id and e.target_thread_id != thread_id
        ]
        self.save_group_registry(reg)
        return True

    def delete_group_registry(self, group_id: str) -> bool:
        """Delete group registry file."""
        f = self._get_group_file(group_id)
        if f.exists():
            f.unlink()
            return True
        return False

    def list_registries(self) -> list[dict[str, Any]]:
        """List summary of all group registries in workspace."""
        results = []
        for f in self.registries_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(data)
            except Exception:
                pass
        return results

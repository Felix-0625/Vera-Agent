"""Improvement proposals stored under `<config root>/.agents/evolution/proposals/<proposal_id>/`.

Each proposal directory holds ``proposal.json`` (kind, content, source traces, the Critic's
rationale, status, gate result) and ``diff.md`` (a readable diff against the baseline profile).

Kinds and what adopting them changes:

- ``rule``: a one-line instruction, stored as a ``rule`` memory in the user or project scope.
- ``skill``: a Skill draft (``name`` and SKILL.md text) installed to `.agents/skills/<name>/`.
- ``prompt_overlay``: extra system-prompt text; stored as a rule-kind memory block.
- ``eval_case``: a new eval case draft; never auto-adopted, the user saves it to a cases folder.

Statuses: ``draft`` -> ``gated`` (gate ran) -> ``recommended`` / ``not_recommended``
-> ``adopted`` / ``rejected``; an adopted proposal may later become ``rolled_back``.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROPOSAL_KINDS = ("rule", "skill", "prompt_overlay", "eval_case")
STATUSES = ("draft", "gated", "recommended", "not_recommended", "adopted", "rejected", "rolled_back")
_PROPOSAL_ID = re.compile(r"^prp_[a-z0-9]{12}$")


@dataclass
class Proposal:
    kind: str
    title: str
    content: str
    rationale: str
    proposal_id: str = field(default_factory=lambda: f"prp_{uuid.uuid4().hex[:12]}")
    skill_name: str = ""
    scope: str = "user"
    scope_id: str = ""
    source_trace_ids: list[str] = field(default_factory=list)
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    gate: dict[str, Any] | None = None
    adoption: dict[str, Any] | None = None
    monitor: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render_diff(self) -> str:
        """Markdown diff of what adoption adds; everything is an addition to the baseline profile."""
        header = f"# {self.title}\n\nKind: {self.kind}; scope: {self.scope}{(' ' + self.scope_id) if self.scope_id else ''}\n"
        target = {
            "rule": "rule memory",
            "prompt_overlay": "profile instructions",
            "skill": f".agents/skills/{self.skill_name}/SKILL.md",
            "eval_case": "eval case draft",
        }[self.kind]
        added = "\n".join(f"+ {line}" for line in self.content.splitlines() or [""])
        return f"{header}\n## Rationale\n\n{self.rationale}\n\n## Change ({target})\n\n```diff\n{added}\n```\n"


class ProposalStore:
    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    @classmethod
    def for_state(cls, state: Any) -> ProposalStore:
        return cls(Path(state.projects_config_root) / ".agents" / "evolution" / "proposals")

    def _path(self, proposal_id: str) -> Path:
        if not _PROPOSAL_ID.fullmatch(proposal_id):
            raise LookupError("Proposal not found.")
        return self.directory / proposal_id

    def save(self, proposal: Proposal) -> Proposal:
        if proposal.kind not in PROPOSAL_KINDS or proposal.status not in STATUSES:
            raise ValueError("Unsupported proposal kind or status.")
        proposal.updated_at = time.time()
        path = self._path(proposal.proposal_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "proposal.json").write_text(
            json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (path / "diff.md").write_text(proposal.render_diff(), encoding="utf-8")
        return proposal

    def get(self, proposal_id: str) -> Proposal:
        file = self._path(proposal_id) / "proposal.json"
        if not file.is_file():
            raise LookupError("Proposal not found.")
        return Proposal(**json.loads(file.read_text(encoding="utf-8")))

    def list(self, status: str | None = None) -> list[Proposal]:
        if not self.directory.is_dir():
            return []
        proposals = [
            Proposal(**json.loads(file.read_text(encoding="utf-8")))
            for file in self.directory.glob("prp_*/proposal.json")
        ]
        if status:
            proposals = [item for item in proposals if item.status == status]
        return sorted(proposals, key=lambda item: item.created_at, reverse=True)

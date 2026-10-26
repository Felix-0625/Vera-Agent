"""Versioned agent profiles: what a baseline or candidate configuration adds to the product.

A profile is a JSON file ``<profiles dir>/<profile_id>.json``::

    {"profile_id": "baseline", "version": 3, "parent": null,
     "prompt_overlay": "...", "rules": ["..."], "skills": {"name": "SKILL.md text"},
     "memories": [{"scope": "user", "kind": "preference", "content": "..."}],
     "created_at": 1730000000.0, "note": "..."}

``prompt_overlay`` and ``rules`` are appended to the system prompt through the `{{slot}}`
mechanism of `server/chat/prompt.py`, so their text is never template-rendered. ``skills`` are
written as `.agents/skills/<name>/SKILL.md` in the sandbox and attached to the eval turn;
``memories`` seed the sandbox memory store. The built-in ``baseline`` profile is empty: it
measures the product exactly as shipped. Profiles are immutable once saved; `derive` creates
a new id with ``parent`` set.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass
class AgentProfile:
    profile_id: str = "baseline"
    version: int = 1
    parent: str | None = None
    prompt_overlay: str = ""
    rules: list[str] = field(default_factory=list)
    skills: dict[str, str] = field(default_factory=dict)
    memories: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    note: str = ""

    def __post_init__(self) -> None:
        if not _PROFILE_ID.fullmatch(self.profile_id):
            raise ValueError(f"Invalid profile id: {self.profile_id!r}")
        for name in self.skills:
            if not _SKILL_NAME.fullmatch(name):
                raise ValueError(f"Invalid Skill name in profile: {name!r}")

    def fingerprint(self) -> str:
        """Content hash, so two profiles with the same content compare as the same configuration."""
        content = {key: value for key, value in asdict(self).items() if key not in {"profile_id", "created_at", "note"}}
        content.pop("version", None)
        content.pop("parent", None)
        return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "fingerprint": self.fingerprint()}

    def prompt_slots(self) -> dict[str, str]:
        """Context slots appended to the system prompt; empty for the baseline."""
        slots: dict[str, str] = {}
        if self.rules:
            slots["profile_rules_context"] = "[LEARNED RULES - approved by the user]\n" + "\n".join(
                f"- {rule}" for rule in self.rules
            )
        if self.prompt_overlay.strip():
            slots["profile_overlay_context"] = "[PROFILE INSTRUCTIONS]\n" + self.prompt_overlay.strip()
        return slots

    def derive(self, profile_id: str, note: str = "", **changes: Any) -> AgentProfile:
        """A new profile based on this one with ``changes`` applied (lists and dicts are copied)."""
        values = json.loads(json.dumps(asdict(self)))
        values.update(changes)
        values.update(profile_id=profile_id, version=self.version + 1, parent=self.profile_id, note=note)
        values["created_at"] = time.time()
        return AgentProfile(**values)


BASELINE_PROFILE_ID = "baseline"


def apply_profile_to_prompt(system_prompt: str, prompt_vars: dict[str, str], profile: AgentProfile) -> str:
    """Append the profile's slots to a built system prompt and fill ``prompt_vars`` in place."""
    for name, text in profile.prompt_slots().items():
        prompt_vars[name] = text
        system_prompt += "\n\n{{" + name + "}}"
    return system_prompt


class ProfileStore:
    """Profiles saved as JSON files in one directory (default `<config root>/.agents/evals/profiles`)."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    @classmethod
    def for_config_root(cls, config_root: Path | str) -> ProfileStore:
        return cls(Path(config_root) / ".agents" / "evals" / "profiles")

    def load(self, profile_id: str) -> AgentProfile:
        path = self.directory / f"{profile_id}.json"
        if not path.is_file():
            if profile_id == BASELINE_PROFILE_ID:
                return AgentProfile(profile_id=BASELINE_PROFILE_ID, note="Product as shipped")
            raise FileNotFoundError(f"Profile not found: {profile_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("fingerprint", None)
        return AgentProfile(**data)

    def save(self, profile: AgentProfile) -> Path:
        path = self.directory / f"{profile.profile_id}.json"
        if path.exists():
            raise FileExistsError(
                f"Profiles are immutable; derive a new id instead of overwriting {profile.profile_id}"
            )
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list(self) -> list[dict[str, Any]]:
        profiles = [self.load(BASELINE_PROFILE_ID).to_dict()] if not (self.directory / "baseline.json").exists() else []
        for path in sorted(self.directory.glob("*.json")):
            profiles.append(self.load(path.stem).to_dict())
        return profiles

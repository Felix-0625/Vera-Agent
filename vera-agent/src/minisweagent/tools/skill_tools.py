"""Dynamic skill discovery and loading for Phase 6.

Adheres to Antigravity and Pi-agent skill architecture:
- Discovers skills dynamically from .agents/skills/<name>/SKILL.md
- Parses YAML frontmatter metadata and markdown instructions
- On-demand injection keeps base prompts tiny (< 400 tokens)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """Represents a discovered skill package."""

    name: str
    description: str
    instructions: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillManager:
    """Manages skill discovery, loading, and prompt integration."""

    def __init__(self, root_dirs: list[Path | str] | None = None):
        self.root_dirs = [Path(d).resolve() for d in root_dirs] if root_dirs else []
        self.skills: dict[str, Skill] = {}
        self.refresh()

    def add_search_dir(self, directory: Path | str) -> None:
        p = Path(directory).resolve()
        if p not in self.root_dirs:
            self.root_dirs.append(p)
            self.refresh()

    def refresh(self) -> None:
        """Scan configured root directories for skills."""
        self.skills.clear()
        for root in self.root_dirs:
            if not root.exists():
                continue

            # Check .agents/skills and skills/
            skill_dirs = [
                root / ".agents" / "skills",
                root / "skills",
            ]

            for s_dir in skill_dirs:
                if not s_dir.exists() or not s_dir.is_dir():
                    continue

                for child in s_dir.iterdir():
                    if child.is_dir():
                        skill_file = child / "SKILL.md"
                        if skill_file.exists() and skill_file.is_file():
                            skill = self._parse_skill_file(skill_file, default_name=child.name)
                            if skill:
                                self.skills[skill.name] = skill

    def _parse_skill_file(self, file_path: Path, default_name: str) -> Skill | None:
        """Parse SKILL.md with frontmatter."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Failed to read skill file %s: %e", file_path, e)
            return None

        name = default_name
        description = ""
        instructions = content

        # Check for simple YAML frontmatter (--- ... ---)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                instructions = parts[2].strip()
                for line in frontmatter.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k_clean = k.strip().lower()
                        v_clean = v.strip().strip("\"'")
                        if k_clean == "name":
                            name = v_clean
                        elif k_clean == "description":
                            description = v_clean

        return Skill(
            name=name,
            description=description,
            instructions=instructions,
            path=file_path,
        )

    def list_skills(self) -> list[dict[str, str]]:
        """List all discovered skills."""
        return [
            {"name": s.name, "description": s.description, "path": str(s.path)}
            for s in self.skills.values()
        ]

    def get_skill(self, name: str) -> Skill | None:
        """Retrieve a skill by name."""
        return self.skills.get(name)

    def render_skill_instruction(self, name: str) -> str | None:
        """Render formatted skill instructions for agent prompt injection."""
        skill = self.get_skill(name)
        if not skill:
            return None
        return (
            f"<skill name='{skill.name}'>\n"
            f"<!-- Description: {skill.description} -->\n"
            f"{skill.instructions}\n"
            "</skill>"
        )

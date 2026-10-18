"""Documentation stays navigable and in sync with the code it describes."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _markdown_files(tracked_files: list[str]) -> list[str]:
    return [path for path in tracked_files if path.endswith(".md") and not path.startswith("docs/archive/")]


def test_relative_markdown_links_resolve(tracked_files: list[str]):
    broken: list[str] = []
    for relative in _markdown_files(tracked_files):
        source = REPO_ROOT / relative
        text = re.sub(r"```.*?```", "", source.read_text(encoding="utf-8"), flags=re.DOTALL)
        for target in LINK.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            path_part = target.split("#", 1)[0]
            if path_part and not (source.parent / path_part).exists():
                broken.append(f"{relative}: {target}")
    assert not broken, "Broken relative links:\n" + "\n".join(broken)


def test_api_route_index_is_current():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_api_index.py"), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr


def test_every_documented_environment_variable_is_in_env_example():
    documented = set(
        re.findall(
            r"^\| `([A-Z][A-Z0-9_]+)` \|",
            (REPO_ROOT / "docs" / "CONFIGURATION.md").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    example = set(
        re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", (REPO_ROOT / ".env.example").read_text(encoding="utf-8"), re.MULTILINE)
    )
    assert documented, "docs/CONFIGURATION.md must contain the environment variable table"
    assert documented == example, f"only in docs: {documented - example}; only in .env.example: {example - documented}"


@pytest.mark.parametrize(
    "module",
    sorted((REPO_ROOT / "vera-agent" / "src" / "vera_agent" / "server" / "routes").glob("[!_]*.py")),
    ids=lambda path: path.name,
)
def test_route_modules_document_their_routes(module: Path):
    source = module.read_text(encoding="utf-8")
    docstring = source.split('"""', 2)[1] if source.startswith('"""') else ""
    paths = re.findall(r'(?:Route|WebSocketRoute)\("([^"]+)"', source)
    missing = [path for path in paths if path.split("{")[0].rstrip("/").rsplit("/", 1)[-1] not in docstring]
    assert docstring, f"{module.name} needs a module docstring"
    assert not missing, f"{module.name} docstring does not mention: {missing}"

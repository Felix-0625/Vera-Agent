"""Skill market internals: build the catalog from curated GitHub repositories and download one Skill bundle.

Used by `skills.py`. Nothing here touches the request or the installed Skills; it only talks to GitHub and
returns plain data. Installation is pinned to a full commit SHA and limited to files below the Skill folder.
"""

from __future__ import annotations

import json
import logging
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

logger = logging.getLogger("vera_server.skills")

USER_AGENT = {"User-Agent": "VeraAgent/1.0"}
API_HEADERS = {"Accept": "application/vnd.github+json", **USER_AGENT}
MAX_ARCHIVE_BYTES = 50_000_000
MAX_FILE_BYTES = 1_000_000
MAX_SKILL_BYTES = 5_000_000
MAX_SKILL_FILES = 80
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
_BLOCK_SCALARS = (">", "|", ">-", "|-")


def _get(url: str, headers: dict[str, str], limit: int, timeout: int) -> bytes:
    with urlopen(UrlRequest(url, headers=headers), timeout=timeout) as response:
        return response.read(limit)


def _description_map(repo: str, commit: str, source_id: str) -> dict[str, str]:
    """Descriptions from the repository's SKILLS-MAP.md table (only the Ninja repository publishes one)."""
    if source_id != "ninja-agent-skills":
        return {}
    markdown = _get(
        f"https://raw.githubusercontent.com/{repo}/{commit}/SKILLS-MAP.md", USER_AGENT, 2_000_000, 10
    ).decode("utf-8", errors="replace")
    rows = re.findall(r"^\|\s*([a-zA-Z0-9_-]+)\s*\|\s*(.*?)\s*\|\s*$", markdown, re.M)
    return {f"{source_id}:{name}": re.sub(r"\*\*|`", "", text).strip()[:1200] for name, text in rows}


def load_source(source_id: str, source: dict[str, str]) -> tuple[list[dict], dict[str, str], bool]:
    """Catalog entries and known descriptions for one repository; ``(.., .., False)`` when it is unreachable."""
    repo = source["repo"]
    try:
        commit = json.loads(_get(f"https://api.github.com/repos/{repo}/commits/main", API_HEADERS, 1_000_000, 12))[
            "sha"
        ]
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
        tree = json.loads(_get(tree_url, API_HEADERS, 8_000_000, 15)).get("tree", [])
        descriptions = _description_map(repo, commit, source_id)
        root = source["root"]
        prefix = f"{root}/" if root else ""
        entries = []
        for item in tree:
            path = item.get("path", "")
            match = re.fullmatch(re.escape(prefix) + r"([^/]+)/SKILL\.md", path)
            if item.get("type") == "blob" and match:
                entries.append(
                    {
                        "market_id": f"{source_id}:{match.group(1)}",
                        "name": match.group(1),
                        "source_id": source_id,
                        "source_path": f"{prefix}{match.group(1)}",
                        "skill_file": path,
                        "description": "",
                        "category": source["label"],
                        "source": f"https://github.com/{repo}",
                        "commit": commit,
                    }
                )
        return entries, descriptions, True
    except Exception as error:
        logger.warning("Skill catalog source %s unavailable: %s", repo, error)
        return [], {}, False


def parse_description(content: str) -> str:
    """The ``description`` value from SKILL.md frontmatter, folding ``>``/``|`` block scalars; "" if absent."""
    frontmatter = _FRONTMATTER.match(content)
    if not frontmatter:
        return ""
    lines = frontmatter.group(1).splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^description\s*:", line):
            continue
        value = line.split(":", 1)[1].strip()
        if value not in _BLOCK_SCALARS:
            return value.strip("'\"")[:1200]
        parts = []
        for following in lines[index + 1 :]:
            if following and not following[0].isspace():
                break
            if following.strip():
                parts.append(following.strip())
        return " ".join(parts)[:1200]
    return ""


def _load_description(entry: dict, sources: dict[str, dict[str, str]], known: dict[str, str]) -> tuple[str, str]:
    market_id = entry["market_id"]
    if known.get(market_id):
        return market_id, known[market_id]
    repo = sources[entry["source_id"]]["repo"]
    raw_url = f"https://raw.githubusercontent.com/{repo}/{entry['commit']}/{entry['skill_file']}"
    try:
        content = _get(raw_url, USER_AGENT, 64_000, 10).decode("utf-8", errors="replace")
        return market_id, parse_description(content)
    except Exception as error:
        logger.debug("Skill description unavailable for %s: %s", market_id, error)
        return market_id, ""


def build_catalog(sources: dict[str, dict[str, str]]) -> list[dict[str, Any]] | None:
    """Every Skill in ``sources`` with a description, or None when no repository could be read.

    Repositories and description files are fetched concurrently so a slow one does not serialize the rest.
    """
    entries: list[dict] = []
    known: dict[str, str] = {}
    reachable = 0
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        for source_entries, descriptions, ok in pool.map(lambda item: load_source(*item), sources.items()):
            entries.extend(source_entries)
            known.update(descriptions)
            reachable += ok
    if reachable == 0 or not entries:
        return None
    with ThreadPoolExecutor(max_workers=48) as pool:
        descriptions = dict(pool.map(lambda entry: _load_description(entry, sources, known), entries))
    for entry in entries:
        entry["description"] = descriptions.get(entry["market_id"]) or f"{entry['name']}（{entry['category']}）"
        entry.pop("skill_file", None)
    return entries


def _bundle_files(archive: zipfile.ZipFile, prefix: str) -> list[tuple[str, bytes]]:
    """Regular files below ``prefix`` in a GitHub archive, within the count and size limits; symlinks are skipped."""
    files: list[tuple[str, bytes]] = []
    total = 0
    for item in archive.infolist():
        parts = item.filename.split("/", 1)  # GitHub archives wrap everything in "<repo>-<sha>/"
        if len(parts) != 2 or not parts[1].startswith(prefix) or item.is_dir():
            continue
        relative = parts[1][len(prefix) :]
        relative_path = Path(relative)
        if not relative or relative_path.is_absolute() or ".." in relative_path.parts:
            continue
        if len(files) >= MAX_SKILL_FILES:
            raise ValueError("Upstream Skill exceeds the 80-file installation limit.")
        if item.file_size > MAX_FILE_BYTES or total + item.file_size > MAX_SKILL_BYTES:
            raise ValueError("Upstream Skill exceeds the 5 MB installation limit.")
        if (item.external_attr >> 16) & 0o170000 == 0o120000:
            continue  # never materialize a symbolic link in the workspace
        with archive.open(item) as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) != item.file_size or len(data) > MAX_FILE_BYTES:
            raise ValueError("Upstream Skill contains an invalid file entry.")
        total += len(data)
        files.append((relative, data))
    return files


def download_skill(repo: str, commit: str, source_path: str) -> list[tuple[str, bytes]]:
    """Download the pinned archive of ``repo`` and return the files of the Skill at ``source_path``.

    GitHub's unauthenticated API can be rate limited, so this uses codeload, which also serves the pinned
    commit and keeps multi-file Skill bundles together.
    """
    data = _get(f"https://codeload.github.com/{repo}/zip/{commit}", USER_AGENT, MAX_ARCHIVE_BYTES + 1, 30)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Upstream repository archive exceeds the 50 MB download limit.")
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("Upstream repository returned an invalid archive.") from error
    with archive:
        files = _bundle_files(archive, source_path + "/")
    if not any(relative == "SKILL.md" for relative, _ in files):
        raise ValueError("Upstream skill does not contain SKILL.md.")
    return files

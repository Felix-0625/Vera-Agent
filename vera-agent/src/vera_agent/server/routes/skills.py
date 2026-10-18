"""Skill discovery and market routes.

Routes: GET /api/skills, POST /api/skills/scan, GET /api/skills/market,
POST /api/skills/install, DELETE /api/skills/{name}, PATCH /api/skills/{name}/toggle.

Installed Skills live in `<projects_config_root>/.agents/skills/<name>/SKILL.md`;
disabled names are kept in `skills_config.json`. Skill text is untrusted input.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.skills")

# Marketplace sources are deliberately curated. Installation requests can only
# address these repositories; clients never get to choose a download host.
SKILL_SOURCES = {
    "anthropic": {"repo": "anthropics/skills", "root": "skills", "label": "Anthropic 官方仓库"},
    "cn-agent-skills": {"repo": "Laffey-82/cn-agent-skills", "root": "skills", "label": "社区仓库 · 中文"},
    "ninja-agent-skills": {"repo": "NinjaSln-labs/agent-skills", "root": "", "label": "社区仓库 · NinjaSln"},
    "vercel-agent-skills": {"repo": "vercel-labs/agent-skills", "root": "skills", "label": "Vercel Labs 官方仓库"},
}
_MARKET_CACHE: tuple[float, list[dict]] | None = None
_MARKET_CACHE_TTL_SECONDS = 900
_MARKET_DISK_CACHE_TTL_SECONDS = 21_600
_MARKET_CACHE_VERSION = 2


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _listed_skills(state: ServerState) -> list[dict[str, str | bool]]:
    if not state.skill_mgr:
        return []
    disabled = set(state.load_json_config("skills_config.json", {"disabled_skills": []}).get("disabled_skills", []))
    return [{**skill, "enabled": skill["name"] not in disabled} for skill in state.skill_mgr.list_skills()]


async def list_skills(request: Request) -> JSONResponse:
    state = _get_state(request)
    if state.skill_mgr:
        state.skill_mgr.refresh()
    skills = _listed_skills(state)
    return JSONResponse({"skills": skills})


async def scan_skills(request: Request) -> JSONResponse:
    state = _get_state(request)
    if state.skill_mgr:
        state.skill_mgr.refresh()
    skills = _listed_skills(state)
    return JSONResponse({"skills": skills})


async def delete_skill(request: Request) -> JSONResponse:
    state = _get_state(request)
    skill_name = request.path_params["skill_name"]
    if not state.skill_mgr:
        return JSONResponse({"error": "SkillManager not initialized"}, status_code=500)

    skill = state.skill_mgr.get_skill(skill_name)
    if not skill:
        return JSONResponse({"error": f"Skill '{skill_name}' not found"}, status_code=404)

    skill_dir = skill.path.parent
    if skill_dir.exists():
        shutil.rmtree(skill_dir, ignore_errors=True)

    state.skill_mgr.refresh()
    return JSONResponse({"status": "ok", "deleted_skill": skill_name})


async def toggle_skill(request: Request) -> JSONResponse:
    """Toggles skill enabled/disabled state in skills_config.json."""
    state = _get_state(request)
    skill_name = request.path_params.get("skill_name")
    if not state.skill_mgr or not state.skill_mgr.get_skill(skill_name):
        return JSONResponse({"error": f"Skill '{skill_name}' not found"}, status_code=404)
    cfg = state.load_json_config("skills_config.json", {"disabled_skills": []})
    disabled = set(cfg.get("disabled_skills", []))

    if skill_name in disabled:
        disabled.remove(skill_name)
        status = "enabled"
    else:
        disabled.add(skill_name)
        status = "disabled"

    cfg["disabled_skills"] = list(disabled)
    state.save_json_config("skills_config.json", cfg)
    return JSONResponse({"status": "ok", "skill_name": skill_name, "state": status})


async def get_skills_market(request: Request) -> JSONResponse:
    state = _get_state(request)
    query = request.query_params.get("q", "").strip().casefold()[:100]

    def fetch_market() -> list[dict]:
        global _MARKET_CACHE
        if _MARKET_CACHE and time.monotonic() - _MARKET_CACHE[0] < _MARKET_CACHE_TTL_SECONDS:
            return _MARKET_CACHE[1]
        cache_root = getattr(state, "projects_config_root", state.root_path)
        cache_file = cache_root / ".agents" / "registries" / "skills-market-cache.json"
        stale_market: list[dict] | None = None
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else None
            if isinstance(cached, dict) and isinstance(cached.get("market"), list) and cached["market"]:
                stale_market = cached["market"]
                cache_is_current = cached.get("version") == _MARKET_CACHE_VERSION
                cache_is_fresh = time.time() - float(cached.get("fetched_at", 0)) < _MARKET_DISK_CACHE_TTL_SECONDS
                if cache_is_current and cache_is_fresh:
                    _MARKET_CACHE = (time.monotonic(), stale_market)
                    return stale_market
        except (OSError, ValueError, TypeError):
            pass
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "VeraAgent/1.0"}
        entries: list[dict] = []
        mapped_descriptions: dict[str, str] = {}

        def load_source(source_record: tuple[str, dict]) -> tuple[list[dict], dict[str, str], bool]:
            source_id, source = source_record
            repo = source["repo"]
            try:
                with urlopen(
                    UrlRequest(f"https://api.github.com/repos/{repo}/commits/main", headers=headers), timeout=12
                ) as response:
                    commit = json.loads(response.read(1_000_000))["sha"]
                with urlopen(
                    UrlRequest(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1", headers=headers),
                    timeout=15,
                ) as response:
                    tree = json.loads(response.read(8_000_000)).get("tree", [])
                source_entries: list[dict] = []
                source_descriptions: dict[str, str] = {}
                if source_id == "ninja-agent-skills":
                    map_url = f"https://raw.githubusercontent.com/{repo}/{commit}/SKILLS-MAP.md"
                    with urlopen(UrlRequest(map_url, headers={"User-Agent": "VeraAgent/1.0"}), timeout=10) as response:
                        index_markdown = response.read(2_000_000).decode("utf-8", errors="replace")
                    for skill_name, description in re.findall(
                        r"^\|\s*([a-zA-Z0-9_-]+)\s*\|\s*(.*?)\s*\|\s*$", index_markdown, re.M
                    ):
                        source_descriptions[f"{source_id}:{skill_name}"] = re.sub(r"\*\*|`", "", description).strip()[
                            :1200
                        ]
                root = source["root"]
                prefix = f"{root}/" if root else ""
                for item in tree:
                    path = item.get("path", "")
                    if item.get("type") != "blob" or not path.startswith(prefix):
                        continue
                    match = re.fullmatch(re.escape(prefix) + r"([^/]+)/SKILL\.md", path)
                    if match:
                        source_entries.append(
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
                return source_entries, source_descriptions, True
            except Exception as error:
                logger.warning("Skill catalog source %s unavailable: %s", repo, error)
                return [], {}, False

        # Fetch independent repositories concurrently to avoid serial network waits.
        successful_sources = 0
        with ThreadPoolExecutor(max_workers=len(SKILL_SOURCES)) as pool:
            for source_entries, source_descriptions, succeeded in pool.map(load_source, SKILL_SOURCES.items()):
                entries.extend(source_entries)
                mapped_descriptions.update(source_descriptions)
                successful_sources += succeeded

        if successful_sources == 0 or not entries:
            if stale_market:
                logger.warning("All Skill catalog sources are unavailable; serving the last saved catalog.")
                _MARKET_CACHE = (time.monotonic(), stale_market)
                return stale_market
            raise RuntimeError("No Skill catalog source returned usable entries.")

        def load_description(entry: dict) -> tuple[str, str]:
            if mapped_descriptions.get(entry["market_id"]):
                return entry["market_id"], mapped_descriptions[entry["market_id"]]
            source = SKILL_SOURCES[entry["source_id"]]
            raw_url = f"https://raw.githubusercontent.com/{source['repo']}/{entry['commit']}/{entry['skill_file']}"
            try:
                with urlopen(UrlRequest(raw_url, headers={"User-Agent": "VeraAgent/1.0"}), timeout=10) as response:
                    content = response.read(64_000).decode("utf-8", errors="replace")
                frontmatter = re.match(r"\A---\s*\n(.*?)\n---", content, re.S)
                if not frontmatter:
                    return entry["market_id"], ""
                lines = frontmatter.group(1).splitlines()
                for index, line in enumerate(lines):
                    if re.match(r"^description\s*:", line):
                        value = line.split(":", 1)[1].strip()
                        if value in (">", "|", ">-", "|-"):
                            parts = []
                            for following in lines[index + 1 :]:
                                if following and not following[0].isspace():
                                    break
                                if following.strip():
                                    parts.append(following.strip())
                            value = " ".join(parts)
                        else:
                            value = value.strip("'\"")
                        return entry["market_id"], value[:1200]
            except Exception as error:
                logger.debug("Skill description unavailable for %s: %s", entry["market_id"], error)
            return entry["market_id"], ""

        with ThreadPoolExecutor(max_workers=48) as pool:
            descriptions = dict(pool.map(load_description, entries))
        for entry in entries:
            entry["description"] = descriptions.get(entry["market_id"]) or f"{entry['name']}（{entry['category']}）"
            entry.pop("skill_file", None)
        _MARKET_CACHE = (time.monotonic(), entries)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file = cache_file.with_suffix(f".{os.getpid()}.tmp")
            temporary_file.write_text(
                json.dumps(
                    {"version": _MARKET_CACHE_VERSION, "fetched_at": time.time(), "market": entries}, ensure_ascii=False
                ),
                encoding="utf-8",
            )
            temporary_file.replace(cache_file)
        except OSError as error:
            logger.warning("Unable to persist Skill market cache: %s", error)
        return entries

    try:
        entries = await asyncio.to_thread(fetch_market)
        if query:
            entries = [
                entry
                for entry in entries
                if query
                in " ".join((entry["name"], entry["description"], entry["category"], entry["source"])).casefold()
            ]
        return JSONResponse(
            {
                "market": entries,
                "sources": [
                    {"id": key, "label": value["label"], "url": f"https://github.com/{value['repo']}"}
                    for key, value in SKILL_SOURCES.items()
                ],
            }
        )
    except Exception as error:
        logger.warning("Skills catalog request failed: %s", error)
        return JSONResponse({"error": "Skill catalogs are currently unavailable.", "market": []}, status_code=502)


async def install_skill(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = body.get("name")
    source_path = body.get("source_path")
    commit = body.get("commit")
    if source_path:
        source_id = body.get("source_id")
        source = SKILL_SOURCES.get(source_id) if isinstance(source_id, str) else None
        root = source["root"] if source else None
        if (
            not source
            or not isinstance(source_path, str)
            or not re.fullmatch((re.escape(root + "/") if root else "") + r"[a-zA-Z0-9_-]+", source_path)
        ):
            return JSONResponse({"error": "Invalid Skill catalog source path."}, status_code=400)
        if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
            return JSONResponse({"error": "A full upstream commit SHA is required."}, status_code=400)
        name = source_path.rsplit("/", 1)[-1]
        skills_root = state.projects_config_root / ".agents" / "skills"
        target_dir = skills_root / name
        if target_dir.exists():
            return JSONResponse({"error": f"Skill '{name}' already exists."}, status_code=409)

        def download_skill() -> list[tuple[str, bytes]]:
            repo = source["repo"]
            # GitHub's unauthenticated API can be rate limited; codeload works
            # against the pinned commit and preserves multi-file Skill bundles.
            archive_url = f"https://codeload.github.com/{repo}/zip/{commit}"
            with urlopen(UrlRequest(archive_url, headers={"User-Agent": "VeraAgent/1.0"}), timeout=30) as response:
                archive_data = response.read(50_000_001)
            if len(archive_data) > 50_000_000:
                raise ValueError("Upstream repository archive exceeds the 50 MB download limit.")
            files = []
            total = 0
            prefix = source_path + "/"
            try:
                archive = zipfile.ZipFile(BytesIO(archive_data))
            except zipfile.BadZipFile as error:
                raise ValueError("Upstream repository returned an invalid archive.") from error
            with archive:
                for item in archive.infolist():
                    parts = item.filename.split("/", 1)
                    if len(parts) != 2 or not parts[1].startswith(prefix) or item.is_dir():
                        continue
                    relative = parts[1][len(prefix) :]
                    relative_path = Path(relative)
                    if not relative or relative_path.is_absolute() or ".." in relative_path.parts:
                        continue
                    if len(files) >= 80:
                        raise ValueError("Upstream Skill exceeds the 80-file installation limit.")
                    if item.file_size > 1_000_000 or total + item.file_size > 5_000_000:
                        raise ValueError("Upstream Skill exceeds the 5 MB installation limit.")
                    # Reject symbolic links instead of materializing them in the workspace.
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        continue
                    with archive.open(item) as stream:
                        data = stream.read(1_000_001)
                    if len(data) != item.file_size or len(data) > 1_000_000:
                        raise ValueError("Upstream Skill contains an invalid file entry.")
                    total += len(data)
                    files.append((relative, data))
            if not any(relative == "SKILL.md" for relative, _ in files):
                raise ValueError("Upstream skill does not contain SKILL.md.")
            return files

        try:
            files = await asyncio.to_thread(download_skill)
            skills_root.mkdir(parents=True, exist_ok=True)
            staging_dir = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=skills_root))
            for relative, data in files:
                target = (staging_dir / relative).resolve()
                if staging_dir.resolve() not in target.parents:
                    raise ValueError("Skill file path escapes its installation directory.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if target_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
                return JSONResponse({"error": f"Skill '{name}' was installed by another request."}, status_code=409)
            staging_dir.rename(target_dir)
            if state.skill_mgr:
                state.skill_mgr.refresh()
            return JSONResponse(
                {
                    "status": "ok",
                    "installed_skill": name,
                    "source": f"https://github.com/{source['repo']}",
                    "commit": commit,
                }
            )
        except Exception as error:
            if "staging_dir" in locals():
                shutil.rmtree(staging_dir, ignore_errors=True)
            logger.warning("Skill installation failed for %s: %s", name, error)
            return JSONResponse({"error": str(error)}, status_code=502)
    description = body.get("description", "Installed from VeraAgent Skill Market")
    instructions = body.get("instructions", "# Skill Guidelines\n\nFollow established project conventions.\n")

    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        return JSONResponse({"error": "Skill name is required"}, status_code=400)

    target_dir = state.projects_config_root / ".agents" / "skills" / name
    if target_dir.exists():
        return JSONResponse({"error": f"Skill '{name}' already exists."}, status_code=409)
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_file = target_dir / "SKILL.md"

    content = f"---\nname: {name}\ndescription: {description}\n---\n\n{instructions}\n"
    skill_file.write_text(content, encoding="utf-8")

    if state.skill_mgr:
        state.skill_mgr.refresh()
    return JSONResponse({"status": "ok", "installed_skill": name})


skill_routes = [
    Route("/api/skills", list_skills, methods=["GET"]),
    Route("/api/skills/scan", scan_skills, methods=["POST"]),
    Route("/api/skills/market", get_skills_market, methods=["GET"]),
    Route("/api/skills/install", install_skill, methods=["POST"]),
    Route("/api/skills/{skill_name}", delete_skill, methods=["DELETE"]),
    Route("/api/skills/{skill_name}/toggle", toggle_skill, methods=["PATCH"]),
]

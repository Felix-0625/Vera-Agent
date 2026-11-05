"""Skill discovery and market routes.

Routes: GET /api/skills, GET /api/skills/market, POST /api/skills/install,
DELETE /api/skills/{name}.

Installed Skills live in `<projects_config_root>/.agents/skills/<name>/SKILL.md`;
names listed under `disabled_skills` in `skills_config.json` are hidden from chat (edit the file to
disable one; there is no UI switch). Skill text is untrusted input.
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
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.routes import skill_market
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


def _read_disk_cache(cache_file: Path) -> tuple[list[dict] | None, bool]:
    """``(market, is_fresh)`` from the saved catalog; ``is_fresh`` needs the current version and a recent fetch."""
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else None
        if isinstance(cached, dict) and isinstance(cached.get("market"), list) and cached["market"]:
            fresh = (
                cached.get("version") == _MARKET_CACHE_VERSION
                and time.time() - float(cached.get("fetched_at", 0)) < _MARKET_DISK_CACHE_TTL_SECONDS
            )
            return cached["market"], fresh
    except (OSError, ValueError, TypeError):
        pass
    return None, False


def _write_disk_cache(cache_file: Path, market: list[dict]) -> None:
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = cache_file.with_suffix(f".{os.getpid()}.tmp")
        payload = {"version": _MARKET_CACHE_VERSION, "fetched_at": time.time(), "market": market}
        temporary_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary_file.replace(cache_file)
    except OSError as error:
        logger.warning("Unable to persist Skill market cache: %s", error)


def _market_catalog(state: ServerState) -> list[dict]:
    """The Skill catalog: memory cache, then fresh disk cache, then GitHub, then a stale disk cache as a fallback."""
    global _MARKET_CACHE
    if _MARKET_CACHE and time.monotonic() - _MARKET_CACHE[0] < _MARKET_CACHE_TTL_SECONDS:
        return _MARKET_CACHE[1]
    cache_root = getattr(state, "projects_config_root", state.root_path)
    cache_file = cache_root / ".agents" / "registries" / "skills-market-cache.json"
    saved, fresh = _read_disk_cache(cache_file)
    if saved is not None and fresh:
        _MARKET_CACHE = (time.monotonic(), saved)
        return saved
    entries = skill_market.build_catalog(SKILL_SOURCES)
    if entries is None:
        if saved is None:
            raise RuntimeError("No Skill catalog source returned usable entries.")
        logger.warning("All Skill catalog sources are unavailable; serving the last saved catalog.")
        _MARKET_CACHE = (time.monotonic(), saved)
        return saved
    _MARKET_CACHE = (time.monotonic(), entries)
    _write_disk_cache(cache_file, entries)
    return entries


async def get_skills_market(request: Request) -> JSONResponse:
    state = _get_state(request)
    query = request.query_params.get("q", "").strip().casefold()[:100]
    try:
        entries = await asyncio.to_thread(_market_catalog, state)
    except Exception as error:
        logger.warning("Skills catalog request failed: %s", error)
        return JSONResponse({"error": "Skill catalogs are currently unavailable.", "market": []}, status_code=502)
    if query:
        entries = [
            entry
            for entry in entries
            if query in " ".join((entry["name"], entry["description"], entry["category"], entry["source"])).casefold()
        ]
    sources = [
        {"id": key, "label": value["label"], "url": f"https://github.com/{value['repo']}"}
        for key, value in SKILL_SOURCES.items()
    ]
    return JSONResponse({"market": entries, "sources": sources})


def _catalog_source(body: dict) -> dict[str, str] | None:
    """The curated source a catalog install names, or None when the source or path is not an exact catalog entry."""
    source_id = body.get("source_id")
    source = SKILL_SOURCES.get(source_id) if isinstance(source_id, str) else None
    source_path = body.get("source_path")
    if not source or not isinstance(source_path, str):
        return None
    root = source["root"]
    return source if re.fullmatch((re.escape(root + "/") if root else "") + r"[a-zA-Z0-9_-]+", source_path) else None


async def _install_from_catalog(state: ServerState, body: dict) -> JSONResponse:
    """Install a catalog Skill from its pinned upstream commit; files are staged and moved in as one folder."""
    source = _catalog_source(body)
    if source is None:
        return JSONResponse({"error": "Invalid Skill catalog source path."}, status_code=400)
    commit = body.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        return JSONResponse({"error": "A full upstream commit SHA is required."}, status_code=400)
    source_path = body["source_path"]
    name = source_path.rsplit("/", 1)[-1]
    skills_root = state.projects_config_root / ".agents" / "skills"
    target_dir = skills_root / name
    if target_dir.exists():
        return JSONResponse({"error": f"Skill '{name}' already exists."}, status_code=409)

    staging_dir: Path | None = None
    try:
        files = await asyncio.to_thread(skill_market.download_skill, source["repo"], commit, source_path)
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
    except Exception as error:
        if staging_dir is not None:
            shutil.rmtree(staging_dir, ignore_errors=True)
        logger.warning("Skill installation failed for %s: %s", name, error)
        return JSONResponse({"error": str(error)}, status_code=502)
    if state.skill_mgr:
        state.skill_mgr.refresh()
    return JSONResponse(
        {"status": "ok", "installed_skill": name, "source": f"https://github.com/{source['repo']}", "commit": commit}
    )


def _install_plain(state: ServerState, body: dict) -> JSONResponse:
    """Write a minimal local Skill from a name, description and instructions."""
    name = body.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        return JSONResponse({"error": "Skill name is required"}, status_code=400)
    description = body.get("description", "Installed from VeraAgent Skill Market")
    instructions = body.get("instructions", "# Skill Guidelines\n\nFollow established project conventions.\n")
    target_dir = state.projects_config_root / ".agents" / "skills" / name
    if target_dir.exists():
        return JSONResponse({"error": f"Skill '{name}' already exists."}, status_code=409)
    target_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n{instructions}\n"
    (target_dir / "SKILL.md").write_text(content, encoding="utf-8")
    if state.skill_mgr:
        state.skill_mgr.refresh()
    return JSONResponse({"status": "ok", "installed_skill": name})


async def install_skill(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if body.get("source_path"):
        return await _install_from_catalog(state, body)
    return _install_plain(state, body)


skill_routes = [
    Route("/api/skills", list_skills, methods=["GET"]),
    Route("/api/skills/market", get_skills_market, methods=["GET"]),
    Route("/api/skills/install", install_skill, methods=["POST"]),
    Route("/api/skills/{skill_name}", delete_skill, methods=["DELETE"]),
]

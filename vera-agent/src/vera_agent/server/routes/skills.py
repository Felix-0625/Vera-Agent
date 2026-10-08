"""Tool 8: Skill ecosystem lifecycle, scanning, market, and prompt template management."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.skills")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def list_skills(request: Request) -> JSONResponse:
    state = _get_state(request)
    if state.skill_mgr:
        state.skill_mgr.refresh()
        skills = state.skill_mgr.list_skills()
    else:
        skills = []
    return JSONResponse({"skills": skills})


async def scan_skills(request: Request) -> JSONResponse:
    state = _get_state(request)
    if state.skill_mgr:
        state.skill_mgr.refresh()
        skills = state.skill_mgr.list_skills()
    else:
        skills = []
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
    market_skills = [
        {
            "name": "gitflow-spec",
            "description": "Standard GitFlow branch naming, commit prefixes, and clean PR guidelines.",
            "category": "Workflow & Git",
        },
        {
            "name": "code-review-guidelines",
            "description": "Pre-flight adversarial code review checklists focusing on security, performance, and maintainability.",
            "category": "Code Quality",
        },
        {
            "name": "mcp-server-dev",
            "description": "Architecture, stdio transport, and schema standards for developing Model Context Protocol servers.",
            "category": "Integration",
        },
        {
            "name": "fastapi-expert",
            "description": "Idiomatic patterns for writing high-performance FastAPI/Starlette microservices and Pydantic v2 schemas.",
            "category": "Backend Engineering",
        },
        {
            "name": "react-antd-architect",
            "description": "Ant Design X and React Flow UI/UX standards with 2D linear vector aesthetics.",
            "category": "Frontend Engineering",
        },
    ]
    return JSONResponse({"market": market_skills})


async def install_skill(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    name = body.get("name")
    description = body.get("description", "Installed from VeraAgent Skill Market")
    instructions = body.get("instructions", "# Skill Guidelines\n\nFollow established project conventions.\n")

    if not name:
        return JSONResponse({"error": "Skill name is required"}, status_code=400)

    target_dir = state.root_path / ".agents" / "skills" / name
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

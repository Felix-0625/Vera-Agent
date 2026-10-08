"""Settings management: LLM model configs & testing, permission approvals, and AGENTS.md rules."""

from __future__ import annotations

import logging
import os
import uuid
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.settings")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _get_default_models() -> dict:
    return {
        "models": [
            {
                "id": "model_deepseek",
                "name": "deepseek/deepseek-chat",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "max_tokens": 8192,
                "temperature": 0.2,
                "is_default": True,
            }
        ]
    }


async def get_models(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = state.load_json_config("models_config.json", _get_default_models())
    return JSONResponse(cfg)


async def save_models(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    state.save_json_config("models_config.json", body)
    return JSONResponse({"status": "ok", "config": body})


async def update_single_model(request: Request) -> JSONResponse:
    """Updates or patches a single model, preserving existing api_key if not overwritten."""
    state = _get_state(request)
    model_id = request.path_params.get("model_id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    cfg = state.load_json_config("models_config.json", _get_default_models())
    models = cfg.get("models", [])
    target = next((m for m in models if m.get("id") == model_id), None)

    if not target:
        # If not found by ID, allow creating or return 404
        return JSONResponse({"error": f"Model '{model_id}' not found"}, status_code=404)

    # Patch fields, preserving existing ones
    for k, v in body.items():
        if k == "api_key" and not v:
            continue  # Don't overwrite existing API key with empty string
        target[k] = v

    if body.get("is_default"):
        for m in models:
            if m.get("id") != model_id:
                m["is_default"] = False

    cfg["models"] = models
    state.save_json_config("models_config.json", cfg)
    return JSONResponse({"status": "updated", "model": target})


async def delete_single_model(request: Request) -> JSONResponse:
    state = _get_state(request)
    model_id = request.path_params.get("model_id")
    cfg = state.load_json_config("models_config.json", _get_default_models())
    models = cfg.get("models", [])

    before_len = len(models)
    models = [m for m in models if m.get("id") != model_id]
    if len(models) == before_len:
        return JSONResponse({"error": f"Model '{model_id}' not found"}, status_code=404)

    cfg["models"] = models
    state.save_json_config("models_config.json", cfg)
    return JSONResponse({"status": "deleted", "model_id": model_id})


async def test_model_connection(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    model_name = body.get("model_name") or body.get("name") or "deepseek/deepseek-chat"
    api_key = body.get("api_key")
    base_url = body.get("base_url")

    env_patch = {}
    if api_key:
        env_patch["DEEPSEEK_API_KEY"] = api_key
        env_patch["OPENAI_API_KEY"] = api_key

    try:
        test_model = LitellmModel(
            model_name=model_name,
            allow_empty_tool_calls=True,
            env=env_patch,
        )
        test_model.query([{"role": "user", "content": "ping"}])
        return JSONResponse({"success": True, "message": "Model connection verified successfully."})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


async def get_permissions(request: Request) -> JSONResponse:
    state = _get_state(request)
    default_perm = {
        "default_mode": "confirm",
        "whitelist_actions": ["read", "symbol_search", "check_syntax"],
    }
    cfg = state.load_json_config("permissions_config.json", default_perm)
    return JSONResponse(cfg)


async def save_permissions(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    state.save_json_config("permissions_config.json", body)
    return JSONResponse({"status": "ok", "permissions": body})


async def get_rules(request: Request) -> JSONResponse:
    """Reads project-level AGENTS.md content and metadata."""
    state = _get_state(request)
    agents_md = state.root_path / "AGENTS.md"
    content = ""
    exists = agents_md.exists()
    if exists:
        try:
            content = agents_md.read_text(encoding="utf-8")
        except Exception as e:
            content = f"Error reading AGENTS.md: {e}"

    return JSONResponse({
        "path": "AGENTS.md",
        "exists": exists,
        "content": content,
    })


async def save_rules(request: Request) -> JSONResponse:
    """Writes updated content to AGENTS.md."""
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    content = body.get("content", "")
    agents_md = state.root_path / "AGENTS.md"
    try:
        agents_md.write_text(content, encoding="utf-8")
        return JSONResponse({"status": "saved", "path": "AGENTS.md", "bytes": len(content.encode("utf-8"))})
    except Exception as e:
        return JSONResponse({"error": f"Failed to save AGENTS.md: {e}"}, status_code=500)


settings_routes = [
    Route("/api/settings/models", get_models, methods=["GET"]),
    Route("/api/settings/models", save_models, methods=["POST"]),
    Route("/api/settings/models/{model_id}", update_single_model, methods=["PATCH"]),
    Route("/api/settings/models/{model_id}", delete_single_model, methods=["DELETE"]),
    Route("/api/settings/models/test", test_model_connection, methods=["POST"]),
    Route("/api/settings/permissions", get_permissions, methods=["GET"]),
    Route("/api/settings/permissions", save_permissions, methods=["POST"]),
    Route("/api/settings/rules", get_rules, methods=["GET"]),
    Route("/api/settings/rules", save_rules, methods=["POST"]),
]

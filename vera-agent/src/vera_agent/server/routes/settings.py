"""Settings management: LLM model configs & testing, permission approvals, and AGENTS.md rules."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.models.litellm_model import LitellmModel
from vera_agent.server.model_profile import resolve_litellm_model_name
from vera_agent.server.permissions import normalize_permissions_config, validate_permissions_config
from vera_agent.server.state import ServerState
from vera_agent.server.user_context import (
    delete_user_memory,
    load_context_settings,
    load_user_memories,
    save_context_settings,
    upsert_user_memory,
)

logger = logging.getLogger("vera_server.settings")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _validate_model(model: object) -> str | None:
    if not isinstance(model, dict):
        return "Each model must be an object."
    string_fields = ("id", "name", "provider", "display_name", "base_url", "api_key")
    for field in string_fields:
        if field in model and model[field] is not None and not isinstance(model[field], str):
            return f"{field} must be a string."
    if not str(model.get("id", "")).strip() or not str(model.get("name", "")).strip():
        return "Model ID and name are required."
    if model.get("provider", "deepseek") not in {"openai", "anthropic", "google", "deepseek", "openrouter", "ollama", "qwen", "zhipu", "moonshot", "siliconflow", "volcengine", "xai", "mistral", "custom"}:
        return "Unsupported model provider."
    if model.get("thinking_mode", "auto") not in {"auto", "enabled", "disabled"}:
        return "Invalid thinking_mode."
    for field in ("is_default", "enabled", "supports_images"):
        if field in model and not isinstance(model[field], bool):
            return f"{field} must be a boolean."
    for field, minimum, maximum in (
        ("context_window", 1, 2_000_000),
        ("output_tokens", 1, 393_216),
        ("max_tokens", 1, 393_216),
        ("max_tool_calls", 1, 500),
        ("temperature", 0, 2),
        ("top_p", 0, 1),
        ("top_k", 1, 100),
    ):
        value = model.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
            return f"{field} must be between {minimum} and {maximum}."
        if field in {"context_window", "output_tokens", "max_tokens", "max_tool_calls", "top_k"} and not isinstance(value, int):
            return f"{field} must be an integer."
    context_window = model.get("context_window")
    output_tokens = model.get("output_tokens") or model.get("max_tokens")
    if context_window and output_tokens and output_tokens > context_window:
        return "Output token limit cannot exceed the context window."
    base_url = str(model.get("base_url", "")).strip()
    if not base_url:
        return "base_url is required."
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "base_url must be an absolute HTTP or HTTPS URL."
    return None


def _validate_models_config(config: object) -> str | None:
    if not isinstance(config, dict) or not isinstance(config.get("models"), list):
        return "Configuration must contain a models array."
    models = config["models"]
    ids: set[str] = set()
    defaults = 0
    for model in models:
        error = _validate_model(model)
        if error:
            return error
        model_id = model["id"].strip()
        if model_id in ids:
            return f"Duplicate model ID: {model_id}."
        ids.add(model_id)
        defaults += model.get("is_default") is True
    if defaults > 1:
        return "Only one model can be the default."
    return None


def _public_model(model: dict) -> dict:
    return {key: value for key, value in model.items() if key not in {"api_key", "model_family"}}


def _get_default_models() -> dict:
    return {
        "models": [
            {
                "id": "model_deepseek",
                "name": "deepseek/deepseek-chat",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com",
                "max_tokens": 8192,
                "temperature": 0.2,
                "is_default": True,
            }
        ]
    }


async def get_models(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = state.load_json_config("models_config.json", _get_default_models())
    return JSONResponse({**cfg, "models": [_public_model(model) for model in cfg.get("models", [])]})


async def save_models(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if isinstance(body, dict) and "model" in body and "models" not in body:
        new_model = body["model"]
        cfg = state.load_json_config("models_config.json", _get_default_models())
        models = cfg.get("models", []) if isinstance(cfg, dict) else []
        error = _validate_model(new_model)
        if error:
            return JSONResponse({"error": error}, status_code=400)
        if any(model.get("id") == new_model["id"] for model in models):
            return JSONResponse({"error": f"Duplicate model ID: {new_model['id']}."}, status_code=400)
        error = _validate_models_config({"models": [*models, new_model]})
        if error:
            return JSONResponse({"error": error}, status_code=400)
        cfg["models"] = [*models, new_model]
        state.save_json_config("models_config.json", cfg)
        return JSONResponse({"status": "ok"})

    error = _validate_models_config(body)
    if error:
        return JSONResponse({"error": error}, status_code=400)
    state.save_json_config("models_config.json", body)
    return JSONResponse({"status": "ok", "config": {**body, "models": [_public_model(model) for model in body["models"]]}})


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

    if not isinstance(body, dict):
        return JSONResponse({"error": "Model update must be an object."}, status_code=400)
    if body.get("id", model_id) != model_id:
        return JSONResponse({"error": "Model ID cannot be changed."}, status_code=400)
    candidate = {**target, **{k: v for k, v in body.items() if k != "api_key" or v}}
    error = _validate_model(candidate)
    if error:
        return JSONResponse({"error": error}, status_code=400)
    if any(model is not target and model.get("id") == candidate["id"] for model in models):
        return JSONResponse({"error": f"Duplicate model ID: {candidate['id']}."}, status_code=400)

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
    return JSONResponse({"status": "updated", "model": _public_model(target)})


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

    raw_model_name = str(body.get("model_name") or body.get("name") or "").strip()
    if not raw_model_name:
        return JSONResponse({"success": False, "error": "Model ID is required."}, status_code=400)

    base_url = str(body.get("base_url") or "").strip()
    provider = body.get("provider")
    model_name = resolve_litellm_model_name(raw_model_name, provider)
    model_id = body.get("model_id")
    api_key = body.get("api_key")
    if not api_key and model_id:
        state = _get_state(request)
        cfg = state.load_json_config("models_config.json", _get_default_models())
        saved_model = next((item for item in cfg.get("models", []) if item.get("id") == model_id), None)
        api_key = (saved_model or {}).get("api_key")

    model_kwargs = {"max_tokens": 1, "timeout": 8, "num_retries": 0}
    if api_key:
        model_kwargs["api_key"] = api_key
    if base_url:
        model_kwargs["api_base"] = base_url

    try:
        test_model = LitellmModel(
            model_name=model_name,
            model_kwargs=model_kwargs,
            allow_empty_tool_calls=True,
            cost_tracking="ignore_errors",
        )
        test_model.query([{"role": "user", "content": "ping"}], tools=[], retry_attempts=1)
        return JSONResponse({"success": True, "message": "Model connection verified successfully."})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


async def get_permissions(request: Request) -> JSONResponse:
    state = _get_state(request)
    cfg = state.load_json_config("permissions_config.json", {})
    return JSONResponse(normalize_permissions_config(cfg))


async def save_permissions(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    permissions, error = validate_permissions_config(body)
    if error:
        return JSONResponse({"error": error}, status_code=400)
    state.save_json_config("permissions_config.json", permissions)
    return JSONResponse({"status": "ok", "permissions": permissions})


async def get_rules(request: Request) -> JSONResponse:
    """Return the separately stored, global user instruction text."""
    return JSONResponse(load_context_settings(_get_state(request)))


async def save_rules(request: Request) -> JSONResponse:
    """Save user instructions without modifying any project instruction file."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict) or not isinstance(body.get("content"), str):
        return JSONResponse({"error": "content must be a string."}, status_code=400)
    if len(body["content"]) > 50_000:
        return JSONResponse({"error": "User instructions must be 50,000 characters or fewer."}, status_code=413)
    config = save_context_settings(_get_state(request), {"user_rules": body["content"]})
    return JSONResponse({"status": "saved", "content": config["user_rules"]})


async def get_context_settings(request: Request) -> JSONResponse:
    return JSONResponse(load_context_settings(_get_state(request)))


async def save_context_settings_route(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict) or not body:
        return JSONResponse({"error": "Settings must be a non-empty object."}, status_code=400)
    allowed = {"include_agents_md", "memory_enabled"}
    if set(body) - allowed or any(not isinstance(value, bool) for value in body.values()):
        return JSONResponse({"error": "Only include_agents_md and memory_enabled boolean settings are accepted."}, status_code=400)
    return JSONResponse(save_context_settings(_get_state(request), body))


async def get_user_memories(request: Request) -> JSONResponse:
    return JSONResponse({"memories": load_user_memories(_get_state(request))})


async def create_user_memory(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict) or not isinstance(body.get("category"), str) or not isinstance(body.get("content"), str):
        return JSONResponse({"error": "category and content are required."}, status_code=400)
    try:
        memory = upsert_user_memory(_get_state(request), body["category"], body["content"], source="user")
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"memory": memory}, status_code=201)


async def update_user_memory(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(body, dict) or not isinstance(body.get("category"), str) or not isinstance(body.get("content"), str):
        return JSONResponse({"error": "category and content are required."}, status_code=400)
    try:
        memory = upsert_user_memory(_get_state(request), body["category"], body["content"], memory_id=request.path_params["memory_id"], source="user", require_existing=True)
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"memory": memory})


async def remove_user_memory(request: Request) -> JSONResponse:
    if not delete_user_memory(_get_state(request), request.path_params["memory_id"]):
        return JSONResponse({"error": "Memory not found."}, status_code=404)
    return JSONResponse({"status": "deleted"})


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
    Route("/api/settings/context", get_context_settings, methods=["GET"]),
    Route("/api/settings/context", save_context_settings_route, methods=["POST"]),
    Route("/api/settings/user-memories", get_user_memories, methods=["GET"]),
    Route("/api/settings/user-memories", create_user_memory, methods=["POST"]),
    Route("/api/settings/user-memories/{memory_id}", update_user_memory, methods=["PATCH"]),
    Route("/api/settings/user-memories/{memory_id}", remove_user_memory, methods=["DELETE"]),
]

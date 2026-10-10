"""Resolve model settings shared by the chat runtime and context inspector."""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL_NAME = "deepseek/deepseek-chat"


def resolve_model_profile(state: Any, requested_model: str | None = None) -> dict[str, Any]:
    config = state.load_json_config("models_config.json", {})
    models = config.get("models", []) if isinstance(config, dict) else []
    selected = next((item for item in models if requested_model and requested_model in {item.get("id"), item.get("name")}), None)
    if selected is None and not requested_model:
        selected = next((item for item in models if item.get("is_default")), None)
    model_name = str((selected or {}).get("name") or requested_model or DEFAULT_MODEL_NAME)

    context_window = (selected or {}).get("context_window")
    context_source = "模型配置" if isinstance(context_window, int) and context_window > 0 else "LiteLLM 模型元数据"
    if not isinstance(context_window, int) or context_window <= 0:
        try:
            import litellm

            context_window = litellm.get_model_info(model_name).get("max_input_tokens")
        except Exception:
            context_window = None

    model_kwargs: dict[str, Any] = {}
    output_tokens = (selected or {}).get("output_tokens") or (selected or {}).get("max_tokens")
    if output_tokens:
        model_kwargs["max_tokens"] = int(output_tokens)
    for config_key, request_key in (("temperature", "temperature"), ("top_p", "top_p"), ("top_k", "top_k")):
        value = (selected or {}).get(config_key)
        if value is not None:
            model_kwargs[request_key] = value
    if (selected or {}).get("api_key"):
        model_kwargs["api_key"] = selected["api_key"]
    if (selected or {}).get("base_url"):
        model_kwargs["api_base"] = selected["base_url"]

    return {
        "name": model_name,
        "config": selected or {},
        "context_window": int(context_window) if isinstance(context_window, (int, float)) and context_window > 0 else None,
        "context_source": context_source,
        "model_kwargs": model_kwargs,
    }

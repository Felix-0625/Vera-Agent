"""Resolve model settings shared by the chat runtime and context inspector."""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL_NAME = "deepseek/deepseek-chat"
DEFAULT_MODEL_CONFIG = {
    "id": "model_deepseek",
    "name": DEFAULT_MODEL_NAME,
    "provider": "deepseek",
    "base_url": "https://api.deepseek.com",
    "max_tokens": 8192,
    "temperature": 0.2,
    "is_default": True,
}


def resolve_litellm_model_name(name: str, provider: str | None = None) -> str:
    """Use LiteLLM's provider-qualified IDs when the UI stores a bare model ID."""
    model_name = name.strip()
    if not provider:
        return model_name
    prefixes = {
        "openai": "openai/",
        "google": "gemini/",
        "deepseek": "deepseek/",
        "anthropic": "anthropic/",
        "ollama": "ollama_chat/",
        "openrouter": "openrouter/",
        "qwen": "dashscope/",
        "zhipu": "zai/",
        "moonshot": "moonshot/",
        # SiliconFlow exposes an OpenAI-compatible endpoint.
        "siliconflow": "openai/",
        "volcengine": "volcengine/",
        "xai": "xai/",
        "mistral": "mistral/",
        # Custom endpoints in this UI follow the OpenAI chat-completions contract.
        "custom": "openai/",
    }
    prefix = prefixes.get(provider, "")
    if prefix and model_name.startswith(prefix):
        return model_name
    if provider == "custom" and any(model_name.startswith(item) for item in prefixes.values()):
        return model_name
    return f"{prefix}{model_name}"


def resolve_model_profile(state: Any, requested_model: str | None = None) -> dict[str, Any]:
    """Resolve a saved model by ID, with safe default selection for older clients.

    Display names remain accepted for legacy callers. Without an explicit model,
    use the configured default or the only enabled model; ambiguous or stale
    selections are rejected instead of silently using environment credentials.
    """
    config = state.load_json_config("models_config.json", {"models": [DEFAULT_MODEL_CONFIG]})
    models = [item for item in config.get("models", []) if isinstance(item, dict)] if isinstance(config, dict) else []
    selected = next((item for item in models if requested_model and item.get("id") == requested_model), None)
    if selected is None:
        selected = next((item for item in models if requested_model and item.get("name") == requested_model), None)
    if requested_model and selected is None and models:
        raise ValueError(f"Configured model '{requested_model}' was not found. Refresh the model list and select an available model.")
    if selected is None and not requested_model:
        enabled_models = [item for item in models if item.get("enabled") is not False]
        selected = next((item for item in enabled_models if item.get("is_default") is True), None)
        if selected is None and len(enabled_models) == 1:
            selected = enabled_models[0]
        elif selected is None and enabled_models:
            raise ValueError("No default model is configured. Select a model in the model picker.")
        elif selected is None and models:
            raise ValueError("No enabled model is configured. Enable a model in Settings.")
    if selected is not None and selected.get("enabled") is False:
        raise ValueError(f"Configured model '{requested_model or selected.get('name')}' is disabled. Select an enabled model.")
    raw_model_name = str((selected or {}).get("name") or requested_model or DEFAULT_MODEL_NAME)
    model_name = resolve_litellm_model_name(raw_model_name, (selected or {}).get("provider"))

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
    # DeepSeek documents this as an OpenAI-compatible extra_body field. Other
    # providers have different thinking controls, so do not send a guessed
    # cross-provider parameter.
    if (selected or {}).get("provider") == "deepseek":
        thinking_mode = (selected or {}).get("thinking_mode", "auto")
        if thinking_mode in {"enabled", "disabled"}:
            model_kwargs["extra_body"] = {"thinking": {"type": thinking_mode}}

    return {
        "name": model_name,
        "config": selected or {},
        "context_window": int(context_window) if isinstance(context_window, (int, float)) and context_window > 0 else None,
        "context_source": context_source,
        "model_kwargs": model_kwargs,
    }

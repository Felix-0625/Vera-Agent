"""LiteLLM chat-completion adapter and streaming tools."""

import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import litellm
from pydantic import BaseModel

from vera_agent.exceptions import FormatError
from vera_agent.models import GLOBAL_MODEL_STATS
from vera_agent.models.utils.actions_toolcall import (
    ALL_TOOLS,
    format_toolcall_observation_messages,
    parse_toolcall_actions,
)
from vera_agent.models.utils.anthropic_utils import _reorder_anthropic_thinking_blocks
from vera_agent.models.utils.cache_control import set_cache_control
from vera_agent.models.utils.openai_multimodal import expand_multimodal_content
from vera_agent.models.utils.retry import retry

logger = logging.getLogger("litellm_model")


class _StreamFailedAfterOutputError(Exception):
    def __init__(self, original: Exception):
        super().__init__(str(original))
        self.original = original


class LitellmModelConfig(BaseModel):
    model_name: str
    """Model name. Highly recommended to include the provider in the model name, e.g., `anthropic/claude-sonnet-4-5-20250929`."""
    model_kwargs: dict[str, Any] = {}
    """Additional arguments passed to the API."""
    litellm_model_registry: Path | str | None = os.getenv("LITELLM_MODEL_REGISTRY_PATH")
    """Model registry for cost tracking and model metadata. See the local model guide (https://mini-swe-agent.com/latest/models/local_models/) for more details."""
    set_cache_control: Literal["default_end"] | None = None
    """Set explicit cache control markers, for example for Anthropic models"""
    cost_tracking: Literal["default", "ignore_errors"] = os.getenv("MSWEA_COST_TRACKING", "default")
    """Cost tracking mode for this model. Can be "default" or "ignore_errors" (ignore errors/missing cost info)"""
    format_error_template: str = "{{ error }}"
    """Template used when the LM's output is not in the expected format."""
    observation_template: str = (
        "{% if output.exception_info %}<exception>{{output.exception_info}}</exception>\n{% endif %}"
        "<returncode>{{output.returncode}}</returncode>\n<output>\n{{output.output}}</output>"
    )
    """Template used to render the observation after executing an action."""
    multimodal_regex: str = ""
    """Regex to extract multimodal content. Empty string disables multimodal processing."""
    allow_empty_tool_calls: bool = False
    dynamic_tool_names: list[str] = []
    """Allow empty tool calls (natural language response without actions)."""


class LitellmModel:
    abort_exceptions: list[type[Exception]] = [
        litellm.exceptions.UnsupportedParamsError,
        litellm.exceptions.NotFoundError,
        litellm.exceptions.PermissionDeniedError,
        litellm.exceptions.ContextWindowExceededError,
        litellm.exceptions.AuthenticationError,
        litellm.exceptions.BadRequestError,
        KeyboardInterrupt,
    ]

    def __init__(self, *, config_class: Callable = LitellmModelConfig, **kwargs):
        self.config = config_class(**kwargs)
        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():
            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))

    def get_tools_for_role(self, role: str = "main") -> list[dict]:
        """Return dynamic tool schema definitions matching the agent's role (Pi-agent philosophy)."""
        from vera_agent.tools import MAIN_AGENT_TOOLS, RESEARCHER_TOOLS, REVIEWER_TOOLS

        if role == "main":
            return MAIN_AGENT_TOOLS
        elif role == "researcher":
            return RESEARCHER_TOOLS
        return REVIEWER_TOOLS

    def _query(self, messages: list[dict[str, str]], tools: list[dict] | None = None, **kwargs):
        call_kwargs = dict(
            model=self.config.model_name,
            messages=messages,
            **(self.config.model_kwargs | kwargs),
        )
        tool_list = tools if tools is not None else ALL_TOOLS
        if tool_list:
            call_kwargs["tools"] = tool_list
        try:
            return litellm.completion(**call_kwargs)
        except litellm.exceptions.AuthenticationError as e:
            e.message += " You can permanently set your API key with `mini-extra config set KEY VALUE`."
            raise e

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        prepared = [{k: v for k, v in msg.items() if k != "extra"} for msg in messages if msg.get("role") != "exit"]
        if "deepseek" in self.config.model_name.casefold():
            # DeepSeek requires every prior assistant turn to carry this field
            # when tools are enabled, including turns with no reasoning tokens.
            prepared = [
                (
                    {**message, "reasoning_content": message.get("reasoning_content") or ""}
                    if message.get("role") == "assistant"
                    else message
                )
                for message in prepared
            ]
        prepared = _reorder_anthropic_thinking_blocks(prepared)
        return set_cache_control(prepared, mode=self.config.set_cache_control)

    def query(self, messages: list[dict[str, str]], tools: list[dict] | None = None, **kwargs) -> dict:
        passed_tools = tools if tools is not None else kwargs.pop("tools", None)
        retry_attempts = kwargs.pop("retry_attempts", None)
        for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions, max_attempts=retry_attempts):
            with attempt:
                response = self._query(self._prepare_messages_for_api(messages), tools=passed_tools, **kwargs)
        cost_output = self._calculate_cost(response)
        GLOBAL_MODEL_STATS.add(cost_output["cost"])
        # Note: all model.query() implementations must persist the response and cost on FormatError.
        try:
            actions = self._parse_actions(response)
        except FormatError as e:
            e.messages[0]["extra"].update(cost_output)
            try:
                e.messages[0]["extra"]["response"] = response.model_dump(mode="json")
            except Exception:
                # model_dump failed (e.g. unserializable object); fall back to repr
                # so the spec contract ("response MUST be persisted") holds unconditionally.
                e.messages[0]["extra"]["response"] = repr(response)
            raise
        message = response.choices[0].message.model_dump()
        message["extra"] = {
            "actions": actions,
            "response": response.model_dump(),
            **cost_output,
            "timestamp": time.time(),
        }
        return message

    def query_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        *,
        on_text: Callable[[str], None],
        **kwargs,
    ) -> dict:
        """Stream visible assistant text while assembling the normal query result."""
        passed_tools = tools if tools is not None else kwargs.pop("tools", None)
        call_kwargs = dict(kwargs)
        call_kwargs["stream"] = True
        stream_options = dict(call_kwargs.get("stream_options") or {})
        stream_options.setdefault("include_usage", True)
        call_kwargs["stream_options"] = stream_options

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] | None = None
        response_id = None
        created = None
        response_model = self.config.model_name
        finish_reason = None
        streamed_text = False
        try:
            for attempt in retry(
                logger=logger,
                abort_exceptions=[*self.abort_exceptions, _StreamFailedAfterOutputError],
            ):
                with attempt:
                    chunks = self._query(self._prepare_messages_for_api(messages), tools=passed_tools, **call_kwargs)
                    try:
                        for chunk in chunks:
                            response_id = getattr(chunk, "id", response_id)
                            created = getattr(chunk, "created", created)
                            response_model = getattr(chunk, "model", response_model)
                            choices = getattr(chunk, "choices", None) or []
                            if getattr(chunk, "usage", None) is not None:
                                usage = (
                                    chunk.usage.model_dump()
                                    if hasattr(chunk.usage, "model_dump")
                                    else dict(chunk.usage)
                                )
                            if not choices:
                                continue
                            choice = choices[0]
                            finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                            delta = getattr(choice, "delta", None)
                            final_message = getattr(choice, "message", None)
                            final_reasoning = getattr(final_message, "reasoning_content", None)
                            if isinstance(final_reasoning, str) and final_reasoning:
                                accumulated_reasoning = "".join(reasoning_parts)
                                if final_reasoning != accumulated_reasoning:
                                    reasoning_parts = [final_reasoning]
                            if delta is None:
                                continue
                            text = getattr(delta, "content", None)
                            if isinstance(text, str) and text:
                                content_parts.append(text)
                                streamed_text = True
                                on_text(text)
                            reasoning = getattr(delta, "reasoning_content", None)
                            if isinstance(reasoning, str) and reasoning:
                                reasoning_parts.append(reasoning)
                            for call in getattr(delta, "tool_calls", None) or []:
                                index = getattr(call, "index", 0)
                                current = tool_calls.setdefault(
                                    index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                                )
                                if getattr(call, "id", None):
                                    current["id"] = call.id
                                if getattr(call, "type", None):
                                    current["type"] = call.type
                                function = getattr(call, "function", None)
                                if function is not None:
                                    if getattr(function, "name", None):
                                        current["function"]["name"] += function.name
                                    if getattr(function, "arguments", None):
                                        current["function"]["arguments"] += function.arguments
                    except Exception as error:
                        if streamed_text:
                            raise _StreamFailedAfterOutputError(error) from error
                        raise
        except _StreamFailedAfterOutputError as error:
            raise error.original from error

        response = litellm.ModelResponse(
            id=response_id,
            created=created,
            model=response_model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "".join(content_parts) or None,
                        "tool_calls": [tool_calls[index] for index in sorted(tool_calls)] or None,
                    },
                    "finish_reason": finish_reason,
                }
            ],
            usage=usage,
        )
        # Some reasoning models require their reasoning trace to be echoed when
        # a tool call is followed by another model turn. Keep it in the persisted
        # assistant message even though it is not shown in the chat UI.
        if reasoning_parts or "deepseek" in self.config.model_name.casefold():
            response.choices[0].message.reasoning_content = "".join(reasoning_parts)
        cost_output = self._calculate_cost(response)
        GLOBAL_MODEL_STATS.add(cost_output["cost"])
        try:
            actions = self._parse_actions(response)
        except FormatError as e:
            e.messages[0]["extra"].update(cost_output)
            e.messages[0]["extra"]["response"] = response.model_dump(mode="json")
            raise
        message = response.choices[0].message.model_dump()
        if "deepseek" in self.config.model_name.casefold():
            # Keep the field present even when a particular streamed tool turn
            # contains no reasoning tokens; DeepSeek validates it on follow-up
            # requests whenever tools are enabled.
            message["reasoning_content"] = "".join(reasoning_parts)
        message["extra"] = {
            "actions": actions,
            "response": response.model_dump(),
            **cost_output,
            "timestamp": time.time(),
        }
        return message

    def _calculate_cost(self, response) -> dict[str, float]:
        try:
            cost = litellm.cost_calculator.completion_cost(response, model=self.config.model_name)
            if cost <= 0.0:
                raise ValueError(f"Cost must be > 0.0, got {cost}")
        except Exception as e:
            cost = 0.0
            if self.config.cost_tracking != "ignore_errors":
                msg = (
                    f"Error calculating cost for model {self.config.model_name}: {e}, perhaps it's not registered? "
                    "You can ignore this issue from your config file with cost_tracking: 'ignore_errors' or "
                    "globally with export MSWEA_COST_TRACKING='ignore_errors'. "
                    "Alternatively check the 'Cost tracking' section in the documentation at "
                    "https://klieret.short.gy/mini-local-models. "
                    " Still stuck? Please open a github issue at https://github.com/SWE-agent/mini-swe-agent/issues/new/choose!"
                )
                logger.critical(msg)
                raise RuntimeError(msg) from e
        return {"cost": cost}

    def _parse_actions(self, response) -> list[dict]:
        """Parse tool calls from the response. Raises FormatError if unknown tool."""
        tool_calls = response.choices[0].message.tool_calls or []
        return parse_toolcall_actions(
            tool_calls,
            format_error_template=self.config.format_error_template,
            template_kwargs={"finish_reason": response.choices[0].finish_reason},
            allow_empty=getattr(self.config, "allow_empty_tool_calls", False),
            additional_tool_names=set(self.config.dynamic_tool_names),
        )

    def format_message(self, **kwargs) -> dict:
        return expand_multimodal_content(kwargs, pattern=self.config.multimodal_regex)

    def format_observation_messages(
        self, message: dict, outputs: list[dict], template_vars: dict | None = None
    ) -> list[dict]:
        """Format execution outputs into tool result messages."""
        actions = message.get("extra", {}).get("actions", [])
        return format_toolcall_observation_messages(
            actions=actions,
            outputs=outputs,
            observation_template=self.config.observation_template,
            template_vars=template_vars,
            multimodal_regex=self.config.multimodal_regex,
        )

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return self.config.model_dump()

    def serialize(self) -> dict:
        return {
            "info": {
                "config": {
                    "model": self.config.model_dump(mode="json"),
                    "model_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                },
            }
        }

"""LiteLLM Responses API model adapter."""

import logging
import time
from collections.abc import Callable

import litellm

from vera_agent.exceptions import FormatError
from vera_agent.models import GLOBAL_MODEL_STATS
from vera_agent.models.litellm_model import LitellmModel, LitellmModelConfig
from vera_agent.models.utils.actions_toolcall_response import (
    ALL_TOOLS_RESPONSE_API,
    finish_reason_from_responses_api,
    format_toolcall_observation_messages,
    parse_toolcall_actions_response,
)
from vera_agent.models.utils.retry import retry

logger = logging.getLogger("litellm_response_model")


class LitellmResponseModelConfig(LitellmModelConfig):
    pass


class LitellmResponseModel(LitellmModel):
    def __init__(self, *, config_class: Callable = LitellmResponseModelConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        """Flatten response objects into their output items for stateless API calls."""
        result = []
        for msg in messages:
            if msg.get("role") == "exit":
                continue
            if msg.get("object") == "response":
                for item in msg.get("output", []):
                    result.append({k: v for k, v in item.items() if k != "extra"})
            else:
                result.append({k: v for k, v in msg.items() if k != "extra"})
        return result

    def get_tools_for_role(self, role: str = "main") -> list[dict]:
        """Return dynamic Response API tool definitions matching the agent's role."""
        from vera_agent.tools import (
            MAIN_AGENT_TOOLS_RESPONSE_API,
            RESEARCHER_TOOLS_RESPONSE_API,
            REVIEWER_TOOLS_RESPONSE_API,
        )

        if role == "main":
            return MAIN_AGENT_TOOLS_RESPONSE_API
        elif role == "researcher":
            return RESEARCHER_TOOLS_RESPONSE_API
        return REVIEWER_TOOLS_RESPONSE_API

    def _query(self, messages: list[dict[str, str]], tools: list[dict] | None = None, **kwargs):
        call_kwargs = dict(
            model=self.config.model_name,
            input=messages,
            **(self.config.model_kwargs | kwargs),
        )
        tool_list = tools if tools is not None else ALL_TOOLS_RESPONSE_API
        if tool_list:
            call_kwargs["tools"] = tool_list
        try:
            return litellm.responses(**call_kwargs)
        except litellm.exceptions.AuthenticationError as e:
            e.message += " You can permanently set your API key with `mini-extra config set KEY VALUE`."
            raise e

    def query(self, messages: list[dict[str, str]], tools: list[dict] | None = None, **kwargs) -> dict:
        passed_tools = tools if tools is not None else kwargs.pop("tools", None)
        for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions):
            with attempt:
                response = self._query(self._prepare_messages_for_api(messages), tools=passed_tools, **kwargs)
        cost_output = self._calculate_cost(response)
        GLOBAL_MODEL_STATS.add(cost_output["cost"])
        try:
            actions = self._parse_actions(response)
        except FormatError as e:
            e.messages[0]["extra"].update(cost_output)
            # hasattr guard: litellm.responses() returns a pydantic object, but tests
            # may inject a plain dict; dict(response) is the correct fallback in that case.
            # Inner try: if serialization itself fails, repr() guarantees the key is always set.
            try:
                e.messages[0]["extra"]["response"] = (
                    response.model_dump(mode="json") if hasattr(response, "model_dump") else dict(response)
                )
            except Exception:
                e.messages[0]["extra"]["response"] = repr(response)
            raise
        message = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        message["extra"] = {
            "actions": actions,
            **cost_output,
            "timestamp": time.time(),
        }
        return message

    def _parse_actions(self, response) -> list[dict]:
        return parse_toolcall_actions_response(
            getattr(response, "output", []),
            format_error_template=self.config.format_error_template,
            template_kwargs={"finish_reason": finish_reason_from_responses_api(response)},
        )

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

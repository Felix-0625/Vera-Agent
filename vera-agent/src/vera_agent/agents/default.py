"""Basic agent class. See https://mini-swe-agent.com/latest/advanced/control_flow/ for visual explanation
or https://minimal-agent.com for a tutorial on the basic building principles.
"""

import json
import logging
import time
import traceback
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, Template
from pydantic import BaseModel

from vera_agent import Environment, Model, __version__
from vera_agent.exceptions import FormatError, InterruptAgentFlowError, LimitsExceeded, Submitted, TimeExceeded
from vera_agent.session import ThreadSession
from vera_agent.utils.serialize import recursive_merge


def load_project_context(start_dir: Path | None = None) -> str:
    """Load AGENTS.md files from the project root through the working directory."""
    start = Path(start_dir or Path.cwd()).resolve()
    project_root = start
    while project_root.parent != project_root and not (project_root / ".git").exists():
        project_root = project_root.parent
    if not (project_root / ".git").exists():
        project_root = start

    directories = [project_root, *[project_root / part for part in start.relative_to(project_root).parts]]
    found_files = [directory / "AGENTS.md" for directory in directories if (directory / "AGENTS.md").is_file()]
    sections = []
    for file_path in found_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            try:
                display_path = str(file_path.relative_to(start))
            except ValueError:
                display_path = file_path.name
            sections.append(f'<project_instructions path="{display_path}">\n{content}\n</project_instructions>')
        except Exception:
            pass

    if sections:
        return "# Project Context\n\nThe following project context files have been loaded:\n\n" + "\n\n".join(sections)
    return ""


class AgentConfig(BaseModel):
    """Check the config files in vera_agent/config for example settings."""

    system_template: str
    """Template for the system message (the first message)."""
    instance_template: str
    """Template for the first user message specifying the task (the second message overall)."""
    role: str = "main"
    """Agent role (e.g., 'main', 'researcher', 'reviewer')."""
    complete_on_empty_actions: bool = False
    """Automatically submit and complete turn when the model produces no actions (Pi-agent style for subagents/batch)."""
    step_limit: int = 0
    """Maximum number of steps the agent can take."""
    cost_limit: float = 3.0
    """Stop agent after exceeding (!) this cost."""
    wall_time_limit_seconds: int = 0
    """Stop agent after this many seconds of wall-clock time. 0 means no limit."""
    max_consecutive_format_errors: int = 3
    """Exit after this many format errors in a row (0 = no limit)."""
    output_path: Path | None = None
    """Save the trajectory to this path."""


class DefaultAgent:
    def __init__(self, model: Model, env: Environment, *, config_class: type = AgentConfig, **kwargs):
        """See the `AgentConfig` class for permitted keyword arguments."""
        self.config = config_class(**kwargs)
        session = kwargs.get("session")
        if session is not None and isinstance(session, ThreadSession):
            self.session = session
        else:
            self.session = ThreadSession(
                role=self.config.role,
                metadata={"config": self.config.model_dump(mode="json")},
            )
        self.messages: list[dict] = self.session.messages
        self.model = model
        self.env = env
        if getattr(self.config, "complete_on_empty_actions", False):
            if hasattr(self.model, "config") and hasattr(self.model.config, "allow_empty_tool_calls"):
                self.model.config.allow_empty_tool_calls = True
        self.extra_template_vars = {}
        self.logger = logging.getLogger("agent")
        self.cost = 0.0
        self.n_calls = 0
        self.n_consecutive_format_errors = 0
        self._start_time = time.time()
        self.progress_callback = None

    def report_progress(self, event: dict) -> None:
        """Report public execution progress when this agent runs as a subagent."""
        if self.progress_callback:
            self.progress_callback(event)

    def get_template_vars(self, **kwargs) -> dict:
        """Recursively merge dictionaries, Integrating data from multiple sources"""
        return recursive_merge(
            self.config.model_dump(),
            self.env.get_template_vars(),
            self.model.get_template_vars(),
            {
                "n_model_calls": self.n_calls,
                "model_cost": self.cost,
                "elapsed_seconds": int(time.time() - self._start_time),
                "project_context": load_project_context(),
            },
            self.extra_template_vars,
            kwargs,
        )

    def _render_template(self, template: str) -> str:
        return Template(template, undefined=StrictUndefined).render(**self.get_template_vars())

    def add_messages(self, *messages: dict) -> list[dict]:
        self.logger.debug(messages)  # set log level to debug to see
        return self.session.add_messages(*messages)

    def handle_uncaught_exception(self, e: Exception) -> list[dict]:
        return self.add_messages(
            self.model.format_message(
                role="exit",
                content=str(e),
                extra={
                    "exit_status": type(e).__name__,
                    "submission": "",
                    "exception_str": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
        )

    def run(self, task: str = "", clear_messages: bool = True, **kwargs) -> dict:
        """Run step() until agent is finished. Returns dictionary with exit_status, submission keys."""
        self.extra_template_vars |= {"task": task, **kwargs}
        if clear_messages:
            self.session.messages.clear()
            self.session.metadata.pop("context_checkpoints", None)
            self.session.metadata.pop("context_events", None)
            self.add_messages(
                self.model.format_message(role="system", content=self._render_template(self.config.system_template)),
                self.model.format_message(role="user", content=self._render_template(self.config.instance_template)),
            )
        else:
            # Multi-turn continuation: pop trailing 'exit' marker from previous run if present
            while self.session.messages and self.session.messages[-1].get("role") == "exit":
                self.session.messages.pop()
            if task:
                self.add_messages(
                    self.model.format_message(
                        role="user", content=self._render_template(self.config.instance_template)
                    ),
                )
        while True:
            try:
                self.step()
                self.n_consecutive_format_errors = 0  # reset on any clean step
            except FormatError as e:
                # The call was billed before parsing failed, so query() never got to charge it.
                self.cost += e.messages[0].get("extra", {}).get("cost", 0.0)
                self.n_consecutive_format_errors += 1
                if 0 < self.config.max_consecutive_format_errors <= self.n_consecutive_format_errors:
                    self.add_messages(
                        *e.messages,
                        {
                            "role": "exit",
                            "content": "RepeatedFormatError",
                            "extra": {"exit_status": "RepeatedFormatError", "submission": ""},
                        },
                    )
                else:
                    self.add_messages(*e.messages)
            except InterruptAgentFlowError as e:
                self.add_messages(*e.messages)
            except Exception as e:
                self.handle_uncaught_exception(e)
                raise
            finally:
                self.save(self.config.output_path)
            if self.messages[-1].get("role") == "exit":
                break
        return self.messages[-1].get("extra", {})

    def step(self) -> list[dict]:
        """Query the LM, execute actions."""
        return self.execute_actions(self.query())

    def query(self) -> dict:
        """Query the model and return model messages. Override to add hooks."""
        if 0 < self.config.step_limit <= self.n_calls or 0 < self.config.cost_limit <= self.cost:
            raise LimitsExceeded(
                {
                    "role": "exit",
                    "content": "LimitsExceeded",
                    "extra": {"exit_status": "LimitsExceeded", "submission": ""},
                }
            )
        if 0 < self.config.wall_time_limit_seconds <= int(time.time() - self._start_time):
            raise TimeExceeded(
                {
                    "role": "exit",
                    "content": "TimeExceeded",
                    "extra": {"exit_status": "TimeExceeded", "submission": ""},
                }
            )
        self.n_calls += 1
        self.session.n_calls = self.n_calls
        self.report_progress({"kind": "status", "label": "正在分析任务", "detail": f"第 {self.n_calls} 轮模型调用"})
        if getattr(self.config, "role", "main") in {"researcher", "reviewer"}:
            from vera_agent.session.context_management import compact_session, subagent_rebirth_if_needed

            model_name = self.model.config.model_name
            model_kwargs = getattr(self.model.config, "model_kwargs", {}) or {}
            try:
                import litellm

                context_window = int(
                    getattr(self.model, "context_window", None)
                    or litellm.get_model_info(model_name).get("max_input_tokens")
                    or 0
                )
            except Exception:
                context_window = 0
            try:
                event = compact_session(
                    self.session,
                    model_name,
                    model_kwargs,
                    context_window or None,
                )
            except Exception:
                self.logger.exception("Subagent context compaction failed; preserving its current transcript")
                event = None
            if event:
                self.report_progress(
                    {
                        "kind": "status",
                        "label": "压缩上下文",
                        "detail": f"约 {event['before_tokens']:,} → {event['after_tokens']:,} Token（本地估算）",
                    }
                )
            rebirth = subagent_rebirth_if_needed(
                self.session,
                model_name,
                context_window or None,
                model_kwargs=model_kwargs,
            )
            if rebirth:
                self.report_progress({"kind": "status", "label": "子智能体换血", "detail": rebirth["detail"]})
        chat_history = self.session.get_chat_history(prune_stale_observations=True)
        message = self.model.query(chat_history, tools=self.get_tools())
        cost_inc = message.get("extra", {}).get("cost", 0.0)
        self.cost += cost_inc
        self.session.add_cost(cost_inc)
        self.add_messages(message)
        if not message.get("extra", {}).get("actions") and message.get("content"):
            self.report_progress({"kind": "result", "content": str(message["content"])})
        return message

    def get_tools(self) -> list[dict]:
        """Return dynamic tool definitions based on agent role following Pi-agent principles.

        - Main agent gets 4 orthogonal primitives + 2 subagents + 2 web search & fetch tools (MAIN_AGENT_TOOLS)
        - Researcher subagent gets 4 primitives + 2 web search & fetch tools (RESEARCHER_TOOLS)
        - Reviewer subagent gets 4 primitives (REVIEWER_TOOLS)
        """
        if getattr(self, "_tools_disabled", False):
            return []
        if getattr(self.config, "tools", None) is not None:
            return self.config.tools
        role = getattr(self.config, "role", "main")
        if hasattr(self.model, "get_tools_for_role"):
            return self.model.get_tools_for_role(role)
        from vera_agent.tools import MAIN_AGENT_TOOLS, RESEARCHER_TOOLS, REVIEWER_TOOLS

        if role == "main":
            return MAIN_AGENT_TOOLS
        elif role == "researcher":
            return RESEARCHER_TOOLS
        return REVIEWER_TOOLS

    def compact(self) -> bool:
        """Manually compact the session into a Pi-style context checkpoint."""
        from vera_agent.session.context_management import compact_session

        model_config = getattr(self.model, "config", None)
        model_name = getattr(model_config, "model_name", None)
        if not model_name:
            return False
        event = compact_session(
            self.session,
            model_name,
            getattr(model_config, "model_kwargs", {}),
            getattr(self.model, "context_window", None),
            force=True,
        )
        return event is not None

    def execute_actions(self, message: dict) -> list[dict]:
        """Execute actions in message, add observation messages, return them."""
        actions = message.get("extra", {}).get("actions", [])
        if not actions and self.config.complete_on_empty_actions:
            raise Submitted(
                {
                    "role": "exit",
                    "content": message.get("content", ""),
                    "extra": {"exit_status": "Submitted", "submission": message.get("content", "")},
                }
            )
        outputs = []
        for action in actions:
            tool_name = action.get("tool_name")
            labels = {
                "read": "读取文件",
                "write": "创建文件",
                "edit": "修改文件",
                "web_search": "网页搜索",
                "fetch_web_page": "读取网页",
            }
            label = labels.get(str(tool_name), str(tool_name or "终端命令"))
            self.report_progress({"kind": "tool", "label": label, "detail": "执行中", "status": "working"})
            if tool_name in ("delegate_research", "delegate_review"):
                outputs.append(self.execute_subagent_tool(action))
            elif tool_name in ("web_search", "fetch_web_page"):
                outputs.append(self.execute_web_tool(action))
            else:
                outputs.append(self.env.execute(action))
            self.report_progress({"kind": "tool", "label": label, "detail": "已完成", "status": "done"})
        return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))

    def execute_subagent_tool(self, action: dict, on_progress=None) -> dict[str, Any]:
        """Dispatch subagent execution (delegate_research or delegate_review) under context isolation."""
        from vera_agent.tools.subagent_tools import execute_subagent

        tool_name = action.get("tool_name", "")
        role = "researcher" if tool_name == "delegate_research" else "reviewer"
        task = action.get("task", "")
        return execute_subagent(self, role=role, task=task, on_progress=on_progress)

    def execute_web_tool(self, action: dict) -> dict[str, Any]:
        """Dispatch external web search or web page fetch."""
        from vera_agent.tools.web_tools import fetch_web_page_op, web_search_op

        tool_name = action.get("tool_name", "")
        if tool_name == "web_search":
            return web_search_op(
                query=action.get("query", ""),
                num_results=action.get("num_results", 5),
            )
        elif tool_name == "fetch_web_page":
            return fetch_web_page_op(
                url=action.get("url", ""),
                max_chars=action.get("max_chars", 8000),
            )
        return {"output": f"Unknown web tool '{tool_name}'", "returncode": 1}

    def serialize(self, *extra_dicts) -> dict:
        """Serialize agent state to a json-compatible nested dictionary for saving."""
        self.session.cost = self.cost
        self.session.n_calls = self.n_calls
        last_message = self.messages[-1] if self.messages else {}
        last_extra = last_message.get("extra", {})
        agent_data = {
            "info": {
                "model_stats": {
                    "instance_cost": self.cost,
                    "api_calls": self.n_calls,
                },
                "config": {
                    "agent": self.config.model_dump(mode="json"),
                    "agent_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                },
                "session": self.session.to_dict(),
                "vera_version": __version__,
                "exit_status": last_extra.get("exit_status", ""),
                "submission": last_extra.get("submission", ""),
            },
            "messages": self.messages,
            "trajectory_format": "vera-agent-1.0",
        }
        return recursive_merge(agent_data, self.model.serialize(), self.env.serialize(), *extra_dicts)

    def export_handover_summary(self, target_role: str = "main", extra_notes: str = "") -> str:
        """Export a structured context handover brief from the current session."""
        self.session.cost = self.cost
        self.session.n_calls = self.n_calls
        return self.session.export_handover_summary(target_role=target_role, extra_notes=extra_notes)

    def save(self, path: Path | None, *extra_dicts) -> dict:
        """Save the trajectory of the agent to a file if path is given. Returns full serialized data.
        You can pass additional dictionaries with extra data to be (recursively) merged into the output data.
        """
        data = self.serialize(*extra_dicts)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2))
        return data

"""Parent permission and write-boundary enforcement for subagent tools."""

from pathlib import Path


class SubagentWorkspaceEnvironment:
    """Apply the parent's action whitelist and isolate child write tools."""

    def __init__(self, inner, root: Path, workspace: Path, parent):
        self._inner = inner
        self._root = root
        self._workspace = workspace
        self.config = inner.config
        self.parent = parent
        self.after_read = None

    def execute(self, action: dict, *args, **kwargs):
        from vera_agent.server.permissions import (
            permission_category,
            record_tool_result,
            requires_approval,
            reserve_tool_call,
        )

        tool_name = str(action.get("tool_name") or ("bash" if "command" in action else ""))
        parent_session = getattr(self.parent, "session", None)
        parent_metadata = getattr(parent_session, "metadata", {})
        group_tools = parent_metadata.get("allowed_tools") if isinstance(parent_metadata, dict) else None
        if getattr(parent_session, "group_id", None) and isinstance(group_tools, list) and tool_name not in group_tools:
            return {
                "output": f"This subagent action is not allowed for the parent group role ({tool_name or 'unknown'}).",
                "returncode": 1,
                "exception_info": "GroupToolDenied",
            }

        category = permission_category(action, str(self._root))
        mode = getattr(self.parent, "permission_mode", "manual")
        approval_actions = getattr(self.parent, "permission_approval_actions", [])
        if requires_approval(mode, category, action, approval_actions):
            return {
                "output": f"This subagent action requires approval in the main conversation ({category}); run it from the main agent instead.",
                "returncode": 1,
                "exception_info": "GlobalPermissionDenied",
            }
        budget = getattr(self.parent, "tool_call_budget", None)
        call_key = None
        if isinstance(budget, dict):
            call_key, budget_error = reserve_tool_call(budget, action)
            if budget_error:
                return {
                    "output": budget_error,
                    "returncode": 1,
                    "exception_info": "ToolCallLimitExceeded"
                    if budget_error.startswith("[Tool call limit")
                    else "ToolAttemptLimitExceeded",
                }
        if tool_name == "bash":
            result = self._inner.execute(action, cwd=str(self._workspace), *args, **kwargs)
        else:
            result = self._inner.execute(action, *args, **kwargs)
        if isinstance(budget, dict) and call_key is not None:
            record_tool_result(budget, call_key, result)
        if tool_name == "read" and result.get("returncode", 0) == 0 and self.after_read:
            self.after_read()
        return result

    def __getattr__(self, name):
        return getattr(self._inner, name)

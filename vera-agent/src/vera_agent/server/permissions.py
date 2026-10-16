"""Small, explicit permission policy shared by settings and chat execution."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PERMISSION_MODES = {"allow_all", "auto", "manual"}
PERMISSION_CATEGORIES = {"read", "create", "edit", "terminal", "search", "mcp", "delegation"}
DEFAULT_APPROVAL_ACTIONS = ["create", "edit", "terminal", "search", "mcp", "delegation"]
DEFAULT_OPERATION_SCOPE = "project_write_external_readonly"

# The old "human" value had conflicting UI and backend meanings. Normalize it
# to manual approval so a legacy config cannot silently become less restrictive.
_LEGACY_MODES = {"human": "manual", "yolo": "auto", "confirm": "manual"}


def normalize_permissions_config(config: Any) -> dict[str, Any]:
    """Normalize current and legacy settings into the canonical small schema."""
    if not isinstance(config, dict):
        config = {}

    mode = config.get("default_mode", "manual")
    if isinstance(mode, str):
        mode = _LEGACY_MODES.get(mode, mode)
    if not isinstance(mode, str) or mode not in PERMISSION_MODES:
        mode = "manual"

    actions = config.get("approval_actions")
    if actions is None:
        old_auto_approved = config.get("whitelist_actions")
        if isinstance(old_auto_approved, list):
            actions = sorted(PERMISSION_CATEGORIES - {str(item) for item in old_auto_approved})
            # Older versions grouped web access with MCP and called delegation MCP.
            if "mcp" not in old_auto_approved:
                actions.extend(["search", "delegation"])
        else:
            actions = list(DEFAULT_APPROVAL_ACTIONS)
    if not isinstance(actions, list):
        actions = list(DEFAULT_APPROVAL_ACTIONS)
    actions = list(dict.fromkeys(str(item) for item in actions if str(item) in PERMISSION_CATEGORIES))

    scope = config.get("operation_scope", DEFAULT_OPERATION_SCOPE)
    if not isinstance(scope, str) or scope not in {"project_only", DEFAULT_OPERATION_SCOPE}:
        scope = DEFAULT_OPERATION_SCOPE

    return {
        "default_mode": mode,
        "approval_actions": actions,
        "operation_scope": scope,
        "max_tool_attempts": _normalize_max_tool_attempts(config.get("max_tool_attempts", 3)),
    }


def _normalize_max_tool_attempts(value: Any) -> int:
    if isinstance(value, bool):
        return 3
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        return 3
    return attempts if 1 <= attempts <= 20 else 3


def validate_permissions_config(config: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Validate writes instead of silently accepting malformed policy values."""
    if not isinstance(config, dict):
        return None, "Permissions must be a JSON object."
    mode = config.get("default_mode")
    if not isinstance(mode, str) or mode not in PERMISSION_MODES:
        return None, "default_mode must be 'allow_all', 'auto', or 'manual'."
    actions = config.get("approval_actions")
    if not isinstance(actions, list) or any(not isinstance(item, str) or item not in PERMISSION_CATEGORIES for item in actions):
        return None, "approval_actions must contain only supported permission categories."
    if len(set(actions)) != len(actions):
        return None, "approval_actions must not contain duplicates."
    scope = config.get("operation_scope", DEFAULT_OPERATION_SCOPE)
    if not isinstance(scope, str) or scope not in {"project_only", DEFAULT_OPERATION_SCOPE}:
        return None, "Invalid operation_scope."
    attempts = config.get("max_tool_attempts", 3)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= 20:
        return None, "max_tool_attempts must be an integer between 1 and 20."
    return normalize_permissions_config(config), None


def permission_category(action: dict[str, Any], project_root: str | None = None) -> str:
    """Map actual runtime tools to the categories exposed by the permission UI."""
    name = str(action.get("tool_name") or "")
    if not name and "command" in action:
        return "terminal"
    if name in {"bash", "terminal"}:
        return "terminal"
    if name in {"read", "symbol_search", "check_syntax"}:
        return "read"
    if name == "edit":
        return "edit"
    if name == "write":
        from pathlib import Path

        target = Path(str(action.get("path", "")))
        if project_root and not target.is_absolute():
            target = Path(project_root) / target
        return "edit" if target.exists() else "create"
    if name in {"web_search", "fetch_web_page"}:
        return "search"
    if name in {"delegate_research", "delegate_review"}:
        return "delegation"
    if name.startswith("mcp__") or name.startswith("mcp:"):
        return "mcp"
    return name or "unknown"


_SAFE_SIMPLE_COMMAND = re.compile(r"^[A-Za-z0-9_./\\:\- =\t]+$")
_SAFE_NO_ARGUMENT_COMMANDS = {"pwd", "get-location", "ls", "dir", "get-childitem"}
_SAFE_GIT_COMMANDS = {
    ("git", "status"),
    ("git", "status", "--short"),
    ("git", "diff", "--name-only"),
    ("git", "branch", "--show-current"),
    ("git", "rev-parse", "--show-toplevel"),
}


def is_low_risk_terminal_command(command: Any) -> bool:
    """Best-effort allowlist for simple read-only inspection commands.

    This is an approval convenience only. It is deliberately narrow and is not
    an OS sandbox; anything not confidently recognized requires confirmation.
    """
    if not isinstance(command, str) or not command.strip() or len(command) > 2000:
        return False
    value = command.strip()
    if not _SAFE_SIMPLE_COMMAND.fullmatch(value):
        return False

    parts = tuple(part.lower() for part in value.split())
    return parts in _SAFE_GIT_COMMANDS or (len(parts) == 1 and parts[0] in _SAFE_NO_ARGUMENT_COMMANDS)


def requires_approval(mode: str, category: str, action: dict[str, Any], approval_actions: list[str]) -> bool:
    """Apply mode semantics consistently at the server-side execution gate."""
    if mode == "allow_all":
        return False
    if mode == "manual":
        return category not in PERMISSION_CATEGORIES or category in approval_actions
    if mode == "auto":
        if category in {"read", "search", "create", "edit"}:
            return False
        if category == "terminal":
            return not is_low_risk_terminal_command(action.get("command"))
        return True
    return True


def reserve_tool_call(budget: dict[str, Any], action: dict[str, Any]) -> tuple[str, str | None]:
    """Count one proposed tool action and enforce per-turn and retry limits."""
    signature = json.dumps(
        {name: value for name, value in action.items() if name != "tool_call_id"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    key = hashlib.sha256(signature.encode("utf-8")).hexdigest()
    if int(budget.get("count", 0)) >= int(budget["limit"]):
        return key, f"[Tool call limit reached] This turn is limited to {budget['limit']} tool calls."
    budget["count"] = int(budget.get("count", 0)) + 1
    if budget["failed_attempts"].get(key, 0) >= int(budget["max_attempts"]):
        return key, f"[Tool retry limit reached] This action has already failed {budget['max_attempts']} times."
    return key, None


def record_tool_result(budget: dict[str, Any], key: str, result: dict[str, Any]) -> None:
    if result.get("returncode", 0) == 0:
        budget["failed_attempts"].pop(key, None)
    else:
        budget["failed_attempts"][key] = budget["failed_attempts"].get(key, 0) + 1

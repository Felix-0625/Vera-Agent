"""Permission categories and approval requirements for each settings permission mode."""

from vera_agent.server.permissions import permission_category, requires_approval


def test_permission_modes_match_settings_values():
    read = {"tool_name": "read", "path": "README.md"}
    terminal = {"tool_name": "bash", "command": "git status --short"}

    assert permission_category(read) == "read"
    assert permission_category({"tool_name": "web_search"}) == "search"
    assert permission_category({"tool_name": "delegate_research"}) == "delegation"
    assert requires_approval("allow_all", "terminal", terminal, ["terminal"]) is False
    assert requires_approval("manual", "read", read, []) is False
    assert requires_approval("manual", "read", read, ["read"]) is True
    assert requires_approval("manual", "unknown_tool", {"tool_name": "unknown_tool"}, []) is True
    assert requires_approval("auto", "terminal", terminal, []) is False
    assert requires_approval("auto", "terminal", {"tool_name": "bash", "command": "rm -rf ."}, []) is True
    assert requires_approval("auto", "mcp", {"tool_name": "mcp__server__tool"}, []) is True

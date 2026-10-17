# Tools, permissions, MCP and Skills

## Built-in tool families

The backend exposes project/file operations, terminal execution, Git/worktree operations, session and subagent orchestration, memory/rules, and integration endpoints. The route inventory is in `vera-agent/src/vera_agent/server/app.py`; concrete contracts are defined by the route handlers, tool modules, and the frontend types under `frontend/src/types/`.

Do not treat a UI tab or template as proof of a working backend action. Verify the corresponding request, route, persistence, and returned event before documenting a capability.

## Permission semantics

Permission mode, operation scope, retry limits, and per-tool ask/allow values are separate inputs. The backend is authoritative: it must validate values rather than trusting UI labels. “Project only” is a path policy, not an OS sandbox. Shell commands execute with the current user’s operating-system privileges.

For sensitive changes, review the end-to-end path: persisted setting → API parsing/validation → execution policy → tool handler → frontend label and event. The UI should not translate an “allow” value into a legacy mode such as `human`.

## MCP

The app-level MCP registry is configured in settings. A configured server launches an external process or connects through the configured transport; tool availability depends on that server’s own dependencies and health. Never infer trust from being listed in a marketplace. A small stdio example exposing two fixed, read-only task-fixture tools is available under [`../examples/mcp-server`](../examples/mcp-server/README.md). It uses the official MCP Python SDK and does not represent a vetted third-party server or a production integration.

## Skills

Skills are instruction packages discovered and selected by the backend. A Skill can influence model behavior and may refer the agent to executable tools; its text is untrusted input. Review its files and any referenced scripts. Keep application-level installation scope explicit when describing whether a Skill is available to projects.

## Observable execution

Use tool-call events and returned results for user-visible traces. A useful event should identify the action, input summary, start/end state, and result/error while avoiding secrets and full environment dumps. Do not expose hidden chain-of-thought as a debug feature.

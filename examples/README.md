# VeraAgent examples

Examples are small, runnable ways to understand one VeraAgent workflow. They are not production templates, security certifications, or evidence that a live model run has completed.

## Start here

- [`sample-project/`](sample-project/README.md) shows how a project, task, and conversation fit together in the workstation. It includes a small task brief and project-local rules; bind it in VeraAgent and follow the walkthrough.
- [`mcp-server/`](mcp-server/README.md) is a minimal MCP server built with the official Python SDK. It exposes read-only fixture tasks, not the host filesystem or VeraAgent's private data.

The website's [interactive demo](../website/playground/) is separate from these runnable examples. It uses scripted local data and does not contact VeraAgent, a model provider, or a project on disk.

## Product model

VeraAgent combines a local project workspace and task board with a Pi Agent-inspired conversation loop, multi-agent collaboration, and project workflow/organization instances. The examples focus on these boundaries instead of copying another project's UI or presenting a generic agent benchmark.

When using a real project, templates describe reusable roles and connections; a project instance contains that project's goal and background; a run starts from a conversation and carries its task plus completed upstream outputs to the relevant nodes. The desktop UI and backend remain the source of truth for actual run behavior. See [architecture](../docs/ARCHITECTURE.md) and [workflow/tool contracts](../docs/TOOLS_AND_MCP.md).

Review code and permissions before connecting any third-party MCP server or Skill. A small example is easier to inspect, but it does not make arbitrary extensions safe.

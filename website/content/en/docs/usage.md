# Daily use

## Bind a project and chat

Choose a trusted local directory, then create a conversation under that project. The path determines where tasks, threads, workflow instances, and run records belong. You can enable a project's `AGENTS.md` rules in Settings; those rules affect context, not execution permission.

The chat shows observable model text, tool requests, approvals, and tool results. Before allowing a file change or terminal command, check the action, target path, and parameters. **Binding a project does not create an OS sandbox.**

## Task board

Create an item in the current project with a title, description, status, priority, and labels. You can link it to a conversation in the same project. Linking does not automatically complete the task; inspect the result and update the status explicitly. Archiving hides an item from the normal list. Records live in application-level SQLite, include `project_id` and a version, and reject stale edits.

## Subagents and collaboration windows

Vera Agent can delegate research or review to subagents. Each role has its own thread. Progress and returned results can be observed from the initiating conversation. Observable events are not the model's hidden reasoning. Side conversations may have different persistence rules depending on their thread type.

## Custom organizations and workflows

1. Design a template in the visual editor. An **organization** is a reporting tree with one root, one direct parent per role, no cycles, and only agent nodes. A **workflow** is a more flexible graph with conditions and bounded loops.
2. Instantiate the template in a project, provide the goal and background, then edit roles, nodes, and edges. Templates do not carry model credentials.
3. Start a run from a project conversation and confirm it explicitly. Each run gets isolated threads that do not share history with the instance or other runs.
4. Inspect node inputs, status, output, and errors. Active-branch results flow downstream. A Supervisor reviews the final result and sends it back to the original conversation.

The regular editor and runtime currently support only **Agent, Condition, and Loop**. Conditions need `true`/`false` branches; loops need `repeat`/`exit` branches and have a 1–20 iteration limit. Other protocol-level node names such as `code` and `http` are not currently executable.

The UI schedules nodes **serially**. Refreshing or closing it interrupts an active run. Saved node states remain in `.agents/runs/`, but there is no one-click resume endpoint. See the [data model](../../../../docs/DATA_MODEL.md#workflow-node-and-edge).

## Tools, MCP, and Skills

Built-in tools cover files, terminal, Git, sessions, and delegation. Configure MCP servers, Skills, and permissions in Settings. External extensions can read data or run commands; inspect their source and parameters before enabling them. Actual tool actions are evidenced by chat events and results, not an interface icon. See [Tools and MCP](../../../../docs/TOOLS_AND_MCP.md).

## Traces, long-term memory, and proposals

- **Traces**: inspect model/tool spans, real exit codes, and independent scores. Thumbs feedback is stored separately. A model saying “done” does not override failed verification.
- **Long-term memory**: choose user/project/session scope, search records, inspect history, delete/restore, and accept or reject pending updates. Only the user or proposal adoption can write `rule` records.
- **Improvement proposals**: analysis calls the model; evaluation incurs additional model costs. Only recommended proposals that passed the gate can be confirmed for adoption. Trigger monitoring when needed; a sufficient score drop rolls back adoption. There is no scheduled self-improvement job.

Consolidation, Langfuse, and Mem0 are off by default. Evals and Critic may send isolated fixtures or redacted trace excerpts to the model. Review data scope, model, and cost first. See [Learning loop](../../../../docs/LEARNING_LOOP.md).

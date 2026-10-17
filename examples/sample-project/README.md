# Sample project: plan and track a small task

This fixture demonstrates one useful path through VeraAgent's local workstation: bind a project, read its project rules, create a task, and continue the work in a project conversation.

## Try it in the desktop app

1. Open the task board and bind this directory as a project.
2. Start a conversation in that project and ask the Agent to read `sample_task.md`, summarize its acceptance criteria, and propose a verification plan. The `AGENTS.md` file is project guidance, not a task result.
3. Create a task in the project task board using the same goal. Open or associate the task's project conversation, then use the board to track its state.
4. If you have configured a workflow/organization instance for this project, start it from the relevant project conversation. Inspect the run record for each node's state, upstream inputs, and output; the task board alone does not prove that a workflow ran.

The last step requires a configured instance and a working model provider. This example does not create a model credential, workflow instance, or real Agent output for you.

## What is in this folder

- `AGENTS.md`: a small, human-readable rule file for this project.
- `sample_task.md`: a documentation-only task with explicit acceptance criteria.

There are no credentials, scripts, external APIs, or generated claims of successful checks in this fixture.

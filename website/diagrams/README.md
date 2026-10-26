# VeraAgent system-design diagrams

These diagrams describe the current source implementation. The editable [draw.io workbook](system-design.drawio) has five Chinese pages and five English pages. Open it in diagrams.net; all boxes, arrows, and labels are native editable objects. SVG exports are displayed by the website without requiring a diagram service.

| Diagram | Chinese | English |
| --- | --- | --- |
| Runtime architecture | [SVG](runtime-architecture.svg) | [SVG](runtime-architecture-en.svg) |
| Chat turn and SSE sequence | [SVG](chat-sequence.svg) | [SVG](chat-sequence-en.svg) |
| Template, instance, and run | [SVG](workflow-lifecycle.svg) | [SVG](workflow-lifecycle-en.svg) |
| Local data and configuration roots | [SVG](local-data.svg) | [SVG](local-data-en.svg) |
| Tracing, memory, and controlled improvement | [SVG](learning-loop.svg) | [SVG](learning-loop-en.svg) |

Sources: [architecture](../../docs/ARCHITECTURE.md), [data model](../../docs/DATA_MODEL.md), [learning loop](../../docs/LEARNING_LOOP.md), `server/chat/`, and `frontend/src/components/tools/workflowRunner.ts`. Runtime components inside the API process are not separately deployed services. Eval configuration roots are per sandbox; the local databases use project/scope filters. Online monitoring is user-triggered, not a timer.

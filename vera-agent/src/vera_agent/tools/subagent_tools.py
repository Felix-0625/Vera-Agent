"""Subagent explicit delegation tools (delegate_research / delegate_review) and gating executor.

Follows the core multi-agent coordination principles:
1. Explicit Invocation: Explicitly exposed in the main agent's toolset; no uncontrolled hidden loops.
2. Strict Gating: Researcher is limited to 2 exploratory calls; Reviewer is limited to 1 final pre-merge audit.
3. Context Firewall: Complete conversation isolation between parent and child agents; returns only a refined Handover Summary.
4. Sandbox Reuse: Parent and child agents share the same runtime Environment instance.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from vera_agent.config import get_config_from_spec
from vera_agent.session import ThreadSession

logger = logging.getLogger("subagent_tools")

# ============================================================================
# 1. OpenAI Function Calling Schema
# ============================================================================

DELEGATE_RESEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "delegate_research",
        "description": (
            "Delegate complex codebase reconnaissance and architecture investigation to the read-only Researcher subagent. "
            "STRICT GATING: Only call when exploring 5+ unfamiliar files, complex cross-module dependencies, or evaluating a new technology stack. "
            "PROHIBITED for single-file lookups, simple questions, or known bug locations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Specific research objective, scope, and technical questions to investigate in the codebase.",
                },
            },
            "required": ["task"],
        },
    },
}

DELEGATE_REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "delegate_review",
        "description": (
            "Delegate pre-merge code review and adversarial quality audit to the Reviewer subagent. "
            "STRICT GATING: Only call ONCE as the final quality gate after all implementations are complete and self-smoke tests pass. "
            "PROHIBITED during mid-implementation or before self-testing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Verification scope, modified files to audit, and specific edge cases to test.",
                },
            },
            "required": ["task"],
        },
    },
}

# ============================================================================
# 2. OpenAI Responses API Flat Schema
# ============================================================================

DELEGATE_RESEARCH_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "delegate_research",
    "description": DELEGATE_RESEARCH_TOOL["function"]["description"],
    "parameters": DELEGATE_RESEARCH_TOOL["function"]["parameters"],
}

DELEGATE_REVIEW_TOOL_RESPONSE_API = {
    "type": "function",
    "name": "delegate_review",
    "description": DELEGATE_REVIEW_TOOL["function"]["description"],
    "parameters": DELEGATE_REVIEW_TOOL["function"]["parameters"],
}

SUBAGENT_TOOLS = [DELEGATE_RESEARCH_TOOL, DELEGATE_REVIEW_TOOL]
SUBAGENT_TOOLS_RESPONSE_API = [DELEGATE_RESEARCH_TOOL_RESPONSE_API, DELEGATE_REVIEW_TOOL_RESPONSE_API]
SUBAGENT_TOOL_NAMES = {"delegate_research", "delegate_review"}


# ============================================================================
# 3. Gatekeeper and Execution Engine
# ============================================================================

# Maximum permitted invocation limits per main session
MAX_SUBAGENT_CALLS = {
    "researcher": 2,
    "reviewer": 1,
}


def check_subagent_gating(parent_agent: Any, role: str) -> str | None:
    """Check gating limits for subagent invocation. Returns error reason if blocked, else None."""
    counts = getattr(parent_agent, "_subagent_call_counts", None)
    if counts is None:
        parent_agent._subagent_call_counts = {}
        counts = parent_agent._subagent_call_counts

    current_calls = counts.get(role, 0)
    max_allowed = MAX_SUBAGENT_CALLS.get(role, 1)

    if current_calls >= max_allowed:
        if role == "reviewer":
            return (
                "Gating Blocked: Reviewer subagent can only be invoked ONCE as the final Pre-merge Gate. "
                "You have already performed the final review. Please proceed to submit your work."
            )
        elif role == "researcher":
            return (
                f"Gating Blocked: Researcher subagent maximum call limit ({max_allowed}) reached for this session. "
                "Please synthesize existing findings and proceed with implementation directly."
            )
        else:
            return f"Gating Blocked: Subagent '{role}' call limit ({max_allowed}) reached."

    return None


def execute_subagent(
    parent_agent: Any,
    role: str,
    task: str,
    *,
    config_spec: str | None = None,
) -> dict[str, Any]:
    """Safely dispatch and execute a subagent within the shared environment.

    - Gating Validation: Blocks excess invocations to prevent infinite loops.
    - Context Firewall: Spawns dedicated child session; parent history is not leaked to subagent.
    - Metrics Aggregation: Subagent cost and calls are synchronized back to the parent session.
    - Handover Delivery: Generates standardized Markdown summary as the sole cross-session observation.
    """
    # 1. Pre-execution gating check
    gate_error = check_subagent_gating(parent_agent, role)
    if gate_error:
        logger.warning(f"Subagent '{role}' gated: {gate_error}")
        return {
            "output": f"Error: {gate_error}",
            "returncode": 1,
            "exception_info": "SubagentGatingBlocked",
        }

    # Increment invocation count
    parent_agent._subagent_call_counts[role] = parent_agent._subagent_call_counts.get(role, 0) + 1

    # 2. Load subagent configuration
    cfg_name = config_spec or f"subagents/{role}.yaml"
    try:
        sub_config_dict = get_config_from_spec(cfg_name)
    except Exception as e:
        logger.error(f"Failed to load subagent config for '{role}' from '{cfg_name}': {e}")
        return {
            "output": f"Error: Failed to load config for subagent '{role}': {e}",
            "returncode": 1,
            "exception_info": "ConfigLoadError",
        }

    # 3. Construct child session (linking parent thread_id)
    parent_session_id = parent_agent.session.thread_id if hasattr(parent_agent, "session") else None
    sub_session = ThreadSession(
        role=role,
        parent_thread_id=parent_session_id,
        metadata={"delegated_task": task, "config": sub_config_dict.get("agent", {})},
    )

    # 4. Create dedicated scratchpad workspace and sandboxed subagent environment
    from vera_agent.agents.default import DefaultAgent
    from vera_agent.environments.local import LocalEnvironment

    parent_workspace = Path(getattr(parent_agent.env.config, "cwd", os.getcwd())).resolve()
    sub_scratch = parent_workspace / ".agents" / "scratch" / f"{role}_{sub_session.thread_id}"
    sub_scratch.mkdir(parents=True, exist_ok=True)

    # Subagent environment: workspace root for reads, strict scratchpad restriction for writes
    if isinstance(parent_agent.env, LocalEnvironment):
        sub_env = LocalEnvironment(
            cwd=str(parent_workspace),
            allowed_write_prefix=str(sub_scratch),
            timeout=getattr(parent_agent.env.config, "timeout", 30),
            env=dict(getattr(parent_agent.env.config, "env", {})),
        )
    else:
        sub_env = parent_agent.env

    agent_kwargs = dict(sub_config_dict.get("agent", {}))
    agent_kwargs["session"] = sub_session
    # Ensure subagent finishes when no further actions are generated
    agent_kwargs["complete_on_empty_actions"] = True

    try:
        sub_agent = DefaultAgent(
            model=parent_agent.model,
            env=sub_env,
            **agent_kwargs,
        )
        logger.info(f"Dispatching subagent '{role}' with task: {task[:60]}...")
        info = sub_agent.run(task)
    except Exception as e:
        logger.error(f"Subagent '{role}' execution failed: {e}")
        return {
            "output": f"Error running subagent '{role}': {e}",
            "returncode": 1,
            "exception_info": str(e),
        }

    # 5. Synchronize cost and call counts back to parent agent
    if hasattr(parent_agent, "cost"):
        parent_agent.cost += sub_agent.cost
    if hasattr(parent_agent, "session"):
        parent_agent.session.add_cost(sub_agent.cost)

    # 6. Generate standardized handover summary
    created_files = [str(p.relative_to(parent_workspace)) for p in sub_scratch.glob("**/*") if p.is_file()]
    extra_notes = f"Subagent execution exit status: {info.get('exit_status', 'Unknown')}"
    if created_files:
        extra_notes += f"\n- **Generated Artifacts**: {', '.join(created_files)}"

    handover_report = sub_agent.export_handover_summary(
        target_role=getattr(parent_agent.config, "role", "main"),
        extra_notes=extra_notes,
    )

    output = f"[Subagent Delivery: {role.upper()}]\n\n{handover_report}"
    return {"output": output, "returncode": 0, "exception_info": ""}

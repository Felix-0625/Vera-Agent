"""System prompt assembly for one chat turn.

The prompt is plain text. User-controlled parts (rules, AGENTS.md, memories) are referenced by
`{{name}}` slots and filled by `fill_context_placeholders`; nothing here is rendered by a
template engine, so template syntax inside user text is passed to the model literally.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from vera_agent.server.chat.workflow_prompt import (
    build_control_prompt,
    build_group_prompt,
    workflow_control_response_format,
)
from vera_agent.server.state import ServerState

__all__ = [
    "build_system_prompt",
    "fill_context_placeholders",
    "enabled_attached_skills",
    "workflow_control_response_format",
]
from vera_agent.session.thread import ThreadSession


def enabled_attached_skills(state: ServerState, attached_skills: list[str]) -> list[str]:
    disabled = set(state.load_json_config("skills_config.json", {"disabled_skills": []}).get("disabled_skills", []))
    return [name for name in attached_skills if name not in disabled]


def fill_context_placeholders(prompt: str, values: dict[str, str]) -> str:
    """Insert saved context blocks into the system prompt without a template engine.

    The prompt contains user-controlled text (rules, AGENTS.md, workflow goals, node prompts,
    Skill instructions). Rendering it with Jinja would execute or reject any `{{`/`{%` inside
    that text, so only the known `{{name}}` slots are replaced literally.
    """
    if not values:
        return prompt
    # One pass, so a slot name appearing inside an inserted value is never substituted again.
    pattern = re.compile("|".join(re.escape("{{" + name + "}}") for name in values))
    return pattern.sub(lambda match: values[match.group(0)[2:-2]], prompt)


def build_system_prompt(
    *,
    state: ServerState,
    session: ThreadSession,
    body: dict[str, Any],
    model_profile: dict[str, Any],
    context_settings: dict[str, Any],
    target_cwd: Path,
    attached_skills: list[str],
    user_memory_context: str,
    rule_trigger: str | None,
    ephemeral: bool,
    is_supervisor_review: bool,
    is_control_decision: bool,
    workflow_control: dict[str, Any] | None,
    workflow_context_text: str,
) -> tuple[str, dict[str, str], dict[str, Any] | None]:
    """Return ``(system_prompt, context_prompt_vars, control_response_format)`` for this turn.

    Sections, in order: base instructions and precedence, user rules / AGENTS.md / memories
    (as slots), memory policy, rule-trigger modes, attached Skills, workflow node context
    (goal, role, node prompt with `{{goal}}`/`{{input}}`/`{{upstream}}` filled), Supervisor or
    control-decision instructions. ``control_response_format`` is set only for control decisions.
    """
    control_response_format: dict[str, Any] | None = None
    system_prompt = (
        "You are an expert AI software engineer operating in an isolated GitFlow environment. "
        "Use write tool to create new files, edit tool to update existing files, read to inspect, and bash to test. "
        "Direct all diagnostic logs to stderr and keep answers concise. "
        "When the user explicitly asks you to create, start, or invoke a subagent, call the matching delegate tool immediately; "
        "never say it is created or running until that tool has actually run."
    )
    system_prompt += (
        "\n\n[INSTRUCTION PRECEDENCE] Follow platform and safety constraints first. "
        "When saved context conflicts, follow User Rules over project AGENTS.md instructions. "
        "Treat remembered profile details as helpful, fallible background and defer to what the user says now. "
        "A user's explicit request in this turn takes precedence over their saved preferences and project guidance."
    )
    context_prompt_vars: dict[str, str] = {}
    if context_settings["user_rules"].strip():
        context_prompt_vars["user_rules_context"] = (
            "[USER RULES - user-managed, higher priority than project instructions]\n"
            + context_settings["user_rules"].strip()
        )
        system_prompt += "\n\n{{user_rules_context}}"
    if context_settings["include_agents_md"]:
        from vera_agent.agents.default import load_project_context

        project_context = load_project_context(start_dir=target_cwd)
        if project_context:
            context_prompt_vars["project_instructions_context"] = (
                "[PROJECT INSTRUCTIONS - AGENTS.md]\n" + project_context
            )
            system_prompt += "\n\n{{project_instructions_context}}"
    if user_memory_context:
        context_prompt_vars["user_memory_context"] = user_memory_context
        system_prompt += "\n\n{{user_memory_context}}"
    if context_settings["memory_enabled"] and session.role == "main" and not ephemeral and not session.group_id:
        system_prompt += (
            "\n\n[USER PROFILE MEMORY POLICY] Save a memory only when the user explicitly asks you to remember it, "
            "or when a stable preference/habit is repeated or clearly confirmed and is likely to help in future conversations. "
            "Then call remember_user with one concise, non-sensitive fact. Do not infer a profile from a single ambiguous "
            "request; do not save ordinary task details, project instructions, credentials, or sensitive personal data. "
            "If the user corrects or withdraws a remembered fact, revise it by ID; call forget_user_memory when asked to forget it."
        )
    if rule_trigger == "learn":
        system_prompt += "\n\n[LEARN REQUEST] Review this conversation for one or more durable, non-sensitive user preferences, habits, profile details, or confirmed corrections and save only those that will help future conversations using remember_user."
    if rule_trigger == "plan":
        system_prompt += (
            "\n[PLAN MODE TRIGGERED]: Outline architecture and proposed file changes explicitly before touching code."
        )
    elif rule_trigger == "goal":
        system_prompt += "\n[GOAL MODE TRIGGERED]: Execute autonomously until all acceptance criteria and tests pass."
    elif rule_trigger == "grill-me":
        system_prompt += "\n[GRILL-ME MODE]: Ask one focused clarifying question at a time to expose assumptions, constraints, and edge cases. Do not start implementation until the user confirms the requirements."

    if state.skill_mgr:
        for sk_name in enabled_attached_skills(state, attached_skills):
            sk_text = state.skill_mgr.render_skill_instruction(sk_name)
            if sk_text:
                system_prompt += f"\n\n{sk_text}"

    system_prompt += build_group_prompt(session, body, workflow_context_text, is_supervisor_review)

    if is_control_decision:
        control_prompt, control_response_format = build_control_prompt(workflow_control, model_profile)
        system_prompt += control_prompt

    return system_prompt, context_prompt_vars, control_response_format

"""Orchestration of the slow loop, used by `server/routes/evolution.py`.

`analyze_recent` collects low-score desktop traces, writes an eval case draft for each, asks the
Critic for proposals and stores them as ``draft``. `gate_proposal` runs the eval gate for one
proposal (this calls the model many times: cases x 2 profiles x repeats) and stores the result.
Neither step changes agent behaviour; only `adoption.adopt`, called on the user's request, does.

Settings in `evolution_config.json`: ``critic_model_id``, ``eval_model_id`` (both default to the
default model), ``low_score_threshold`` (0.5), ``gate_repeats`` (3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vera_agent.evals.cases import BUILTIN_CASES_DIR, load_cases
from vera_agent.evals.profile import ProfileStore
from vera_agent.evolution.active_profile import active_profile
from vera_agent.evolution.case_drafts import draft_from_trace
from vera_agent.evolution.critic import ModelCall, criticize
from vera_agent.evolution.gate import SuiteRunner, run_gate, suite_runner
from vera_agent.evolution.proposals import Proposal, ProposalStore
from vera_agent.memory.consolidate import litellm_model_call
from vera_agent.server.model_profile import resolve_model_profile
from vera_agent.telemetry.store import TraceStore

EVOLUTION_CONFIG_FILE = "evolution_config.json"
DEFAULT_EVOLUTION_CONFIG: dict[str, Any] = {
    "critic_model_id": "",
    "eval_model_id": "",
    "low_score_threshold": 0.5,
    "gate_repeats": 3,
}


def load_evolution_config(state: Any) -> dict[str, Any]:
    raw = state.load_json_config(EVOLUTION_CONFIG_FILE, {})
    config = dict(DEFAULT_EVOLUTION_CONFIG)
    if isinstance(raw, dict):
        config.update({key: raw[key] for key in DEFAULT_EVOLUTION_CONFIG if key in raw})
    try:
        config["low_score_threshold"] = max(0.0, min(float(config["low_score_threshold"]), 1.0))
        config["gate_repeats"] = max(1, min(int(config["gate_repeats"]), 10))
    except (TypeError, ValueError):
        return dict(DEFAULT_EVOLUTION_CONFIG)
    return config


def low_score_traces(state: Any, threshold: float, limit: int = 8) -> list[dict[str, Any]]:
    store = TraceStore.for_state(state)
    summaries = store.list_traces(below_score=threshold, exclude_eval=True, limit=limit)
    return [trace for summary in summaries if (trace := store.get_trace(summary["trace_id"])) is not None]


def analyze_recent(state: Any, *, call_model: ModelCall | None = None, limit: int = 8) -> dict[str, Any]:
    config = load_evolution_config(state)
    traces = low_score_traces(state, config["low_score_threshold"], limit)
    drafts = [str(path) for trace in traces if (path := draft_from_trace(state.projects_config_root, trace))]
    if not traces:
        return {"traces": 0, "drafts": drafts, "proposals": []}
    if call_model is None:
        call_model = litellm_model_call(resolve_model_profile(state, config["critic_model_id"] or None))
    store = ProposalStore.for_state(state)
    proposals = [store.save(proposal).to_dict() for proposal in criticize(call_model, traces)]
    return {"traces": len(traces), "drafts": drafts, "proposals": proposals}


def gate_cases(state: Any) -> list:
    project_cases = Path(state.projects_config_root) / ".agents" / "evals" / "cases"
    return load_cases([BUILTIN_CASES_DIR, *([project_cases] if project_cases.is_dir() else [])])


def gate_proposal(state: Any, proposal_id: str, *, runner: SuiteRunner | None = None) -> Proposal:
    store = ProposalStore.for_state(state)
    proposal = store.get(proposal_id)
    if proposal.kind == "eval_case":
        raise ValueError("Eval case proposals are reviewed by the user, not gated.")
    if runner is None:
        config = load_evolution_config(state)
        profile = resolve_model_profile(state, config["eval_model_id"] or None)
        models_config = state.load_json_config("models_config.json", {"models": []})
        runner = suite_runner(models_config, str(profile["config"].get("id", "")), config["gate_repeats"])
    # Measure against what users run today (product + already adopted rules), not the bare product,
    # so a second proposal is judged on top of the first one.
    adopted = active_profile(state, proposal.scope_id if proposal.scope == "project" else None, None)
    baseline = (
        ProfileStore.for_config_root(state.projects_config_root)
        .load("baseline")
        .derive(
            "baseline-active",
            "baseline plus adopted proposals",
            rules=adopted.rules,
            prompt_overlay=adopted.prompt_overlay,
        )
    )
    proposal.gate = run_gate(proposal, baseline, gate_cases(state), runner)
    proposal.status = proposal.gate["status"]
    return store.save(proposal)

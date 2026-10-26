"""The eval gate: does a proposal make the agent better without breaking core abilities?

The proposal is applied to the baseline profile to form a candidate (`candidate_profile`).
Both profiles then run, in order and stopping at the first failure:

1. ``train``: a quick sanity check; the candidate must not be ``worse``.
2. ``holdout``: the decision; the candidate must be ``better`` (bootstrap interval above zero).
3. ``guard``: zero regressions; any guard case the baseline passed on every repeat and the
   candidate failed even once rejects the proposal.

Only a proposal that clears all three is ``recommended``; the user still decides. To keep the
holdout split from leaking into proposals, the stored gate result for holdout keeps aggregate
numbers only (pass counts, interval, verdict), never per-case results or acceptance output.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vera_agent.evals.cases import EvalCase
from vera_agent.evals.compare import compare_profiles, regressions
from vera_agent.evals.profile import AgentProfile
from vera_agent.evolution.proposals import Proposal

SuiteRunner = Callable[[list[EvalCase], list[AgentProfile]], list[Any]]


def candidate_profile(baseline: AgentProfile, proposal: Proposal) -> AgentProfile:
    candidate_id = f"cand-{proposal.proposal_id[4:]}"
    note = f"proposal {proposal.proposal_id}: {proposal.title}"
    if proposal.kind == "rule":
        return baseline.derive(candidate_id, note, rules=[*baseline.rules, proposal.content])
    if proposal.kind == "prompt_overlay":
        overlay = "\n\n".join(part for part in (baseline.prompt_overlay, proposal.content) if part.strip())
        return baseline.derive(candidate_id, note, prompt_overlay=overlay)
    if proposal.kind == "skill":
        return baseline.derive(candidate_id, note, skills={**baseline.skills, proposal.skill_name: proposal.content})
    raise ValueError("Eval case proposals are reviewed by the user, not gated.")


def _stage(
    name: str,
    cases: list[EvalCase],
    runner: SuiteRunner,
    baseline: AgentProfile,
    candidate: AgentProfile,
    *,
    private: bool,
) -> dict[str, Any]:
    results = runner(cases, [baseline, candidate])
    comparison = compare_profiles(results, baseline.profile_id, candidate.profile_id).to_dict()
    stage: dict[str, Any] = {"split": name, "cases": len(cases), **comparison}
    if name == "guard":
        stage["regressions"] = regressions(results, baseline.profile_id, candidate.profile_id)
    if not private:
        stage["results"] = [item if isinstance(item, dict) else item.to_dict() for item in results]
    return stage


def run_gate(
    proposal: Proposal,
    baseline: AgentProfile,
    cases: list[EvalCase],
    runner: SuiteRunner,
) -> dict[str, Any]:
    """Run the three stages and return the gate result (also the proposal's new status)."""
    candidate = candidate_profile(baseline, proposal)
    by_split = {split: [case for case in cases if case.split == split] for split in ("train", "holdout", "guard")}
    if not by_split["holdout"] or not by_split["guard"]:
        return {"status": "not_recommended", "reason": "The gate needs holdout and guard cases.", "stages": []}
    stages: list[dict[str, Any]] = []
    reason = ""
    if by_split["train"]:
        stages.append(_stage("train", by_split["train"], runner, baseline, candidate, private=False))
        if stages[-1]["verdict"] == "worse":
            reason = "Candidate is worse on train cases."
    if not reason:
        stages.append(_stage("holdout", by_split["holdout"], runner, baseline, candidate, private=True))
        if stages[-1]["verdict"] != "better":
            reason = f"Holdout verdict is {stages[-1]['verdict']}; a proposal must be significantly better."
    if not reason:
        stages.append(_stage("guard", by_split["guard"], runner, baseline, candidate, private=True))
        if stages[-1]["regressions"]:
            reason = f"Guard regressions: {', '.join(stages[-1]['regressions'])}."
    return {
        "status": "not_recommended" if reason else "recommended",
        "reason": reason or "Holdout is significantly better and no guard case regressed.",
        "candidate_profile": candidate.to_dict(),
        "stages": stages,
    }


def suite_runner(models_config: dict[str, Any], model_id: str, repeats: int = 3) -> SuiteRunner:
    """The real runner (calls the model); tests pass a scripted runner instead."""
    # Imported here: the runner imports the server package, whose routes import this module.
    from vera_agent.evals.runner import run_suite

    def run(cases: list[EvalCase], profiles: list[AgentProfile]) -> list[Any]:
        return run_suite(cases, profiles, models_config, model_id, repeats=repeats)

    return run

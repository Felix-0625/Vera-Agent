"""A run that crashed (model or network error) is not evidence about the agent and must not move the gate."""

from vera_agent.evals.cases import parse_case
from vera_agent.evals.compare import case_pass_rates, compare_profiles, error_count
from vera_agent.evals.profile import AgentProfile
from vera_agent.evolution.gate import run_gate
from vera_agent.evolution.proposals import Proposal


def _result(case_id: str, profile_id: str, passed: bool, error: str = "") -> dict:
    return {"case_id": case_id, "profile_id": profile_id, "passed": passed, "error": error}


def test_errored_runs_are_excluded_from_pass_rates():
    results = [_result("c1", "base", True), _result("c1", "base", False, error="RateLimitError")]
    assert case_pass_rates(results, "base") == {"c1": 1.0}
    assert error_count(results) == 1


def test_provider_outage_on_one_side_is_not_a_difference():
    results = []
    for case_id in ("c1", "c2", "c3"):
        results += [_result(case_id, "base", True), _result(case_id, "cand", False, error="ConnectionError")]
    comparison = compare_profiles(results, "base", "cand")
    assert comparison.cases == 0 and comparison.verdict == "no_difference"


def _cases() -> list:
    return [
        parse_case({"id": f"{split}-{i}", "task": "t", "split": split, "accept": "true", "fixture": {"a.txt": "x"}})
        for split in ("train", "holdout", "guard")
        for i in range(2)
    ]


def test_gate_rejects_when_any_run_errored_instead_of_trusting_partial_results():
    proposal = Proposal(kind="rule", title="t", content="Run the tests.", rationale="r")

    def runner(cases, profiles):
        results = []
        for case in cases:
            for profile in profiles:
                broke = profile.profile_id != "baseline" and case.case_id == "holdout-0"
                results.append(
                    _result(case.case_id, profile.profile_id, passed=not broke, error="Timeout" if broke else "")
                )
        return results

    outcome = run_gate(proposal, AgentProfile(), _cases(), runner)

    assert outcome["status"] == "not_recommended"
    assert "failed to execute" in outcome["reason"] and "holdout" in outcome["reason"]
    assert [stage["split"] for stage in outcome["stages"]] == ["train", "holdout"]

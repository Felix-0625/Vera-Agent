"""Paired comparison of two profiles on the same cases.

Each case is run N times per profile; its pass rate per profile is the mean over repeats. The
comparison works on per-case differences (candidate minus baseline), so easy and hard cases do
not drown each other out:

- ``win_rate``: share of cases with a non-zero difference that the candidate wins (ties excluded).
- ``mean_delta`` with a percentile bootstrap interval over cases (``confidence`` default 0.95).
- ``sign_test_p``: two-sided exact sign test on winning versus losing cases.

Verdict: ``better`` when the interval lies above zero, ``worse`` when it lies below zero, and
``no_difference`` otherwise. With few cases the interval is wide and most comparisons end as
``no_difference``; that is the honest result, not a bug. The bootstrap uses a fixed seed so a
report is reproducible from its inputs.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

VERDICTS = ("better", "no_difference", "worse")


@dataclass
class Comparison:
    """The outcome of comparing a candidate profile with a baseline on the cases both ran."""

    baseline: str
    candidate: str
    cases: int
    wins: int
    losses: int
    ties: int
    baseline_pass_rate: float
    candidate_pass_rate: float
    mean_delta: float
    ci_low: float
    ci_high: float
    win_rate: float | None
    sign_test_p: float
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_dict(result: Any) -> dict[str, Any]:
    return result if isinstance(result, dict) else result.to_dict()


def error_count(results: list[Any]) -> int:
    """Runs that could not be judged (model or infrastructure failure), not agent failures."""
    return sum(bool(_as_dict(result).get("error")) for result in results)


def case_pass_rates(results: list[Any], profile_id: str) -> dict[str, float]:
    """Mean acceptance pass per case for one profile (results are `CaseResult`s or dicts).

    A run with ``error`` set never reached a verdict about the agent, so it is left out instead
    of counting as a failure; otherwise a provider outage on one side would look like a difference.
    """
    passes: dict[str, list[float]] = defaultdict(list)
    for item in map(_as_dict, results):
        if item["profile_id"] == profile_id and not item.get("error"):
            passes[item["case_id"]].append(1.0 if item["passed"] else 0.0)
    return {case_id: sum(values) / len(values) for case_id, values in passes.items()}


def sign_test_p(wins: int, losses: int) -> float:
    """Two-sided exact binomial sign test p-value."""
    trials = wins + losses
    if trials == 0:
        return 1.0
    tail = sum(math.comb(trials, k) for k in range(0, min(wins, losses) + 1)) / 2**trials
    return min(1.0, 2 * tail)


def bootstrap_interval(
    deltas: list[float], confidence: float = 0.95, iterations: int = 2000, seed: int = 0
) -> tuple[float, float]:
    if not deltas:
        return 0.0, 0.0
    if len(set(deltas)) == 1:
        return deltas[0], deltas[0]
    rng = random.Random(seed)
    count = len(deltas)
    means = sorted(sum(rng.choice(deltas) for _ in range(count)) / count for _ in range(iterations))
    alpha = (1 - confidence) / 2
    low_index = int(alpha * iterations)
    high_index = min(iterations - 1, int((1 - alpha) * iterations))
    return means[low_index], means[high_index]


def compare_profiles(results: list[Any], baseline: str, candidate: str, *, confidence: float = 0.95) -> Comparison:
    """Compare ``candidate`` against ``baseline`` on the cases both profiles ran."""
    base_rates, cand_rates = case_pass_rates(results, baseline), case_pass_rates(results, candidate)
    shared = sorted(set(base_rates) & set(cand_rates))
    deltas = [cand_rates[case_id] - base_rates[case_id] for case_id in shared]
    wins = sum(delta > 0 for delta in deltas)
    losses = sum(delta < 0 for delta in deltas)
    low, high = bootstrap_interval(deltas, confidence)
    # A single case cannot establish a difference, however large.
    if len(shared) >= 2 and low > 0:
        verdict = "better"
    elif len(shared) >= 2 and high < 0:
        verdict = "worse"
    else:
        verdict = "no_difference"

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return Comparison(
        baseline=baseline,
        candidate=candidate,
        cases=len(shared),
        wins=wins,
        losses=losses,
        ties=len(shared) - wins - losses,
        baseline_pass_rate=mean([base_rates[case_id] for case_id in shared]),
        candidate_pass_rate=mean([cand_rates[case_id] for case_id in shared]),
        mean_delta=mean(deltas),
        ci_low=round(low, 4),
        ci_high=round(high, 4),
        win_rate=round(wins / (wins + losses), 4) if wins + losses else None,
        sign_test_p=round(sign_test_p(wins, losses), 4),
        verdict=verdict,
    )


def regressions(results: list[Any], baseline: str, candidate: str) -> list[str]:
    """Cases the baseline passed on every repeat that the candidate failed at least once."""
    base_rates, cand_rates = case_pass_rates(results, baseline), case_pass_rates(results, candidate)
    return sorted(case_id for case_id, rate in base_rates.items() if rate == 1.0 and cand_rates.get(case_id, 1.0) < 1.0)

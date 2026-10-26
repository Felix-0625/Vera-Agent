"""Eval reports: per-profile pass rates, pairwise comparisons, and guard regressions.

Reports are saved as JSON under `<config root>/.agents/evals/reports/<report_id>.json` and can be
rendered as a Markdown summary for the terminal or a pull request.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from vera_agent.evals.compare import compare_profiles, regressions


def build_report(results: list[Any], profile_ids: list[str], *, splits: list[str], repeats: int) -> dict[str, Any]:
    items = [result if isinstance(result, dict) else result.to_dict() for result in results]
    per_profile: dict[str, dict[str, Any]] = {}
    for profile_id in profile_ids:
        runs = [item for item in items if item["profile_id"] == profile_id]
        by_split: dict[str, list[bool]] = defaultdict(list)
        for item in runs:
            by_split[item["split"]].append(item["passed"])
        per_profile[profile_id] = {
            "runs": len(runs),
            "passed": sum(item["passed"] for item in runs),
            "pass_rate": round(sum(item["passed"] for item in runs) / len(runs), 4) if runs else 0.0,
            "errors": sum(bool(item["error"]) for item in runs),
            "cost": round(sum(item["cost"] for item in runs), 4),
            "by_split": {split: round(sum(values) / len(values), 4) for split, values in sorted(by_split.items())},
        }
    baseline = profile_ids[0]
    comparisons = []
    for candidate in profile_ids[1:]:
        guard_items = [item for item in items if item["split"] == "guard"]
        comparisons.append(
            {
                **compare_profiles(items, baseline, candidate).to_dict(),
                "guard_regressions": regressions(guard_items, baseline, candidate),
            }
        )
    return {
        "report_id": f"rep_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "created_at": time.time(),
        "splits": splits,
        "repeats": repeats,
        "profiles": per_profile,
        "comparisons": comparisons,
        "results": items,
    }


def save_report(config_root: Path | str, report: dict[str, Any]) -> Path:
    directory = Path(config_root) / ".agents" / "evals" / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report['report_id']}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Eval report {report['report_id']}",
        "",
        f"Splits: {', '.join(report['splits'])}; repeats per case: {report['repeats']}",
        "",
        "| Profile | Runs | Pass rate | Errors | Cost | By split |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for profile_id, summary in report["profiles"].items():
        by_split = ", ".join(f"{split} {rate:.0%}" for split, rate in summary["by_split"].items())
        lines.append(
            f"| {profile_id} | {summary['runs']} | {summary['pass_rate']:.0%} | {summary['errors']} | "
            f"{summary['cost']:.4f} | {by_split} |"
        )
    for comparison in report["comparisons"]:
        lines += [
            "",
            f"## {comparison['candidate']} vs {comparison['baseline']}: **{comparison['verdict']}**",
            "",
            f"- Cases: {comparison['cases']} (wins {comparison['wins']}, losses {comparison['losses']}, "
            f"ties {comparison['ties']})",
            f"- Mean pass-rate delta: {comparison['mean_delta']:+.3f} "
            f"(95% CI {comparison['ci_low']:+.3f} to {comparison['ci_high']:+.3f}); "
            f"sign test p = {comparison['sign_test_p']:.3f}",
            f"- Guard regressions: {', '.join(comparison['guard_regressions']) or 'none'}",
        ]
    return "\n".join(lines) + "\n"

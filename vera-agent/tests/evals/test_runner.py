"""The headless eval runner drives the real chat pipeline with a scripted model (no model API calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.chat_helpers import reply, scripted_stream
from vera_agent.evals.cases import EvalCaseError, parse_case
from vera_agent.evals.profile import AgentProfile, ProfileStore
from vera_agent.evals.report import build_report, render_markdown
from vera_agent.evals.runner import run_case, run_suite

MODELS_CONFIG = {
    "models": [{"id": "m1", "name": "deepseek/deepseek-chat", "provider": "deepseek", "api_key": "x", "enabled": True}]
}

FIX_CASE = parse_case(
    {
        "id": "fix-add",
        "task": "Fix add() in calc.py so the test passes. Do not modify tests/.",
        "split": "holdout",
        "fixture": {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/__init__.py": "",
            "tests/test_calc.py": (
                "import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
                "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n"
            ),
        },
        "accept": "python -m unittest -q",
        "allowed_commands": ["python -m unittest*"],
    }
)


def _fixing_model(fix: bool):
    """Scripted model: optionally edits calc.py, then runs the tests, then answers."""
    edit = {"tool_name": "edit", "path": "calc.py", "edits": [{"oldText": "a - b", "newText": "a + b"}]}
    run_tests = {"command": "python -m unittest -q"}
    responses = (
        [reply("Fixing.", edit), reply("Testing.", run_tests), reply("Done.")] if fix else [reply("Looks fine.")]
    )
    return lambda: scripted_stream(responses)


def test_run_case_passes_when_the_agent_fixes_the_bug():
    result = run_case(FIX_CASE, AgentProfile(), MODELS_CONFIG, "m1", model_factory=_fixing_model(fix=True))
    assert result.error == "", result.error
    assert result.passed and result.exit_status == "finish" and result.steps == 3
    assert [decision["choice"] for decision in result.approvals] == ["Y"]
    span_kinds = [span["kind"] for span in result.trace["spans"]]
    assert span_kinds == ["model", "tool", "model", "tool", "model"]
    assert {score["name"] for score in result.trace["scores"]} >= {"outcome", "verification", "eval_accept"}


def test_run_case_fails_when_the_bug_stays():
    result = run_case(FIX_CASE, AgentProfile(), MODELS_CONFIG, "m1", model_factory=_fixing_model(fix=False))
    assert not result.passed and result.error == ""
    assert "FAILED" in result.acceptance_output or "Error" in result.acceptance_output


def test_commands_outside_the_allowlist_are_rejected_and_never_run(tmp_path: Path):
    marker = tmp_path / "escaped.txt"
    case = parse_case({"id": "deny-shell", "task": "x", "split": "guard", "accept": "true"})
    escape = {"command": f"python -c \"open(r'{marker}', 'w').write('x')\""}
    result = run_case(
        case,
        AgentProfile(),
        MODELS_CONFIG,
        "m1",
        model_factory=lambda: scripted_stream([reply("Go.", escape), reply("Ok.")]),
    )
    assert [(item["category"], item["choice"]) for item in result.approvals] == [("terminal", "N")]
    assert not marker.exists()


def test_profile_rules_reach_the_system_prompt():
    seen: list[str] = []

    def factory():
        from unittest.mock import patch

        from vera_agent.models.litellm_model import LitellmModel

        def capture(_model, messages, tools=None, *, on_text, **_kwargs):
            seen.append(str(messages[0]["content"]))
            return {"role": "assistant", "content": "ok", "extra": {"actions": []}}

        return patch.object(LitellmModel, "query_stream", new=capture)

    profile = AgentProfile(profile_id="cand", rules=["Always run the tests before answering."])
    run_case(FIX_CASE, profile, MODELS_CONFIG, "m1", model_factory=factory)
    assert "[LEARNED RULES - approved by the user]" in seen[0]
    assert "Always run the tests before answering." in seen[0]


def test_suite_report_compares_profiles():
    def factory(_case, profile, _repeat):
        return _fixing_model(fix=profile.profile_id == "cand")()

    profiles = [AgentProfile(), AgentProfile(profile_id="cand")]
    results = run_suite([FIX_CASE], profiles, MODELS_CONFIG, "m1", repeats=1, model_factory=factory)
    report = build_report(results, ["baseline", "cand"], splits=["holdout"], repeats=1)
    assert report["profiles"]["baseline"]["pass_rate"] == 0.0 and report["profiles"]["cand"]["pass_rate"] == 1.0
    comparison = report["comparisons"][0]
    assert comparison["wins"] == 1 and comparison["verdict"] == "no_difference"  # one case cannot prove a difference
    assert "cand vs baseline" in render_markdown(report)


def test_case_validation_rejects_escaping_fixtures():
    for fixture in ({"../x.py": ""}, {"/abs.py": ""}, {".agents/models_config.json": "{}"}):
        with pytest.raises(EvalCaseError):
            parse_case({"id": "bad-case", "task": "t", "split": "train", "accept": "true", "fixture": fixture})


def test_profiles_are_immutable_and_derive_new_versions(tmp_path: Path):
    store = ProfileStore(tmp_path)
    base = store.load("baseline")
    child = base.derive("cand-1", note="adds a rule", rules=["Run tests."])
    store.save(child)
    assert store.load("cand-1").parent == "baseline" and store.load("cand-1").version == 2
    with pytest.raises(FileExistsError):
        store.save(child)
    assert child.fingerprint() != base.fingerprint()
    assert json.loads((tmp_path / "cand-1.json").read_text(encoding="utf-8"))["fingerprint"] == child.fingerprint()

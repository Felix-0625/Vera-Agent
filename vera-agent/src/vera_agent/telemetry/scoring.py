"""Outcome scores for finished turns, computed from outcome signals rather than tool return codes.

Three kinds of evidence, kept as separate score names so they are never silently mixed:

- ``turn_signal`` (source ``signal``): immediate signals of the turn itself — a model error,
  hitting the tool limit, an interruption, rejected approvals, and `O:` corrections.
- ``verification`` (source ``verifier``): the last test or build command the turn ran decides.
- ``user_followup`` (source ``heuristic``): the next user message in the thread, matched against
  correction and acceptance phrases, scores the *previous* trace. It is a weak signal and is
  reported on its own; it never changes ``outcome``.

``outcome`` is ``verification`` when the turn ran one, otherwise ``turn_signal``. Scores are in
[0, 1]; values of 0.5 and above count as a success in the success-rate views. Eval gates only
trust their acceptance scripts (`evals/`), not these scores.
"""

from __future__ import annotations

import re
from typing import Any

from vera_agent.telemetry.trace import Score, Trace

# Programs whose own name already means "run the tests"; every other program below needs a
# test/build subcommand right after it, so `go env` and `make install` are not verification.
_SELF_VERIFYING_PROGRAMS = {"pytest", "unittest", "tox", "nox", "vitest", "jest", "tsc", "check-all"}
_SUBCOMMAND_PROGRAMS = {"npm", "pnpm", "yarn", "cargo", "go", "mvn", "dotnet", "make", "ruff"}
_GRADLE = re.compile(r"^gradle\w*$", re.IGNORECASE)
_VERIFY_SUBCOMMAND = re.compile(r"^(?:run\s+)?(test|build|lint|check|verify|package)\b", re.IGNORECASE)
_PROGRAM_PATH = re.compile(
    r"^(?:\./|\.\\|[\w./-]*/|[A-Za-z]:\\[\w.\\-]*\\)?([\w.-]+?)(?:\.(?:exe|cmd|ps1))?$", re.IGNORECASE
)
# A shell operator anywhere in the command means a later, un-inspected command decides the
# command's real exit code; `echo pytest` and `grep pytest x` must not count as verification either.
_SHELL_COMPOSITION = re.compile(r"[;&|`\n\r]|\$\(")
_INFO_FLAG = {"--version", "-V", "--help", "-h"}


def _program_name(token: str) -> str:
    """The bare program name from an argv token (strips a leading path and a Windows extension)."""
    match = _PROGRAM_PATH.match(token)
    return match.group(1).lower() if match else token.lower()


def is_verification_command(command: str) -> bool:
    """True only when ``command`` itself invokes a test/build tool, not merely mentions one as an
    argument (``echo pytest``, ``grep pytest x``), runs a different but similarly-named module
    (``python -m unittest.mock``), or chains it with something else."""
    if _SHELL_COMPOSITION.search(command):
        return False
    tokens = command.split()
    if not tokens:
        return False
    index = 0
    if _program_name(tokens[0]).startswith("python") and len(tokens) > 2 and tokens[1] == "-m":
        index = 2
    rest_tokens = tokens[index + 1 :]
    # A pure info/metadata flag means the tool was asked about itself, not asked to run anything.
    # It can appear anywhere (`pytest -q --version`), not only as the first argument, and most
    # tools (pytest included) exit 0 and skip the real run the moment it's present.
    if _INFO_FLAG.intersection(rest_tokens):
        return False
    program = _program_name(tokens[index])
    if program in _SELF_VERIFYING_PROGRAMS:
        return True
    if program in _SUBCOMMAND_PROGRAMS or _GRADLE.match(program):
        return bool(_VERIFY_SUBCOMMAND.match(" ".join(rest_tokens)))
    return False


_CORRECTION = re.compile(
    r"(不对|不是这样|错了|有问题|没用|还是不行|不行|回滚|撤销|改回|重新来|别这样|并没有|"
    r"\bwrong\b|\bnot what\b|doesn'?t work|didn'?t work|\brevert\b|\bundo\b|\broll ?back\b|still (?:fails|broken))",
    re.IGNORECASE,
)
_ACCEPTANCE = re.compile(
    r"(谢谢|可以了|好的|没问题|很好|完美|继续|下一步|接着|提交吧|"
    r"\bthanks?\b|\blgtm\b|\bgreat\b|\bperfect\b|\bworks\b|\bnext\b|\bcontinue\b|go ahead)",
    re.IGNORECASE,
)


def _tool_spans(trace: Trace) -> list[Any]:
    return [span for span in trace.spans if span.kind in {"tool", "subagent"}]


def turn_signal_score(trace: Trace) -> Score:
    reasons: list[str] = []
    value = 1.0
    if trace.exit_status == "error":
        value, reasons = 0.0, ["model error"]
    elif trace.exit_status == "interrupted":
        value = min(value, 0.2)
        reasons.append("interrupted")
    spans = _tool_spans(trace)
    if any(str(span.metadata.get("exception_info")) == "ToolCallLimitExceeded" for span in spans):
        value = min(value, 0.3)
        reasons.append("tool limit reached")
    rejected = sum(span.metadata.get("approval") == "rejected" for span in spans)
    corrected = sum(span.metadata.get("approval") == "corrected" for span in spans)
    if rejected:
        value -= 0.2 * rejected
        reasons.append(f"{rejected} approval(s) rejected")
    if corrected:
        value -= 0.3 * corrected
        reasons.append(f"{corrected} correction(s)")
    value = round(max(0.0, min(1.0, value)), 3)
    return Score(trace.trace_id, "turn_signal", value, "signal", "; ".join(reasons) or "completed without issues")


def verification_score(trace: Trace) -> Score | None:
    """Score from the last test/build command the turn ran; None when it ran none."""
    verifications = [
        span
        for span in _tool_spans(trace)
        if span.name == "bash"
        and isinstance(span.input, dict)
        and is_verification_command(str(span.input.get("command", "")))
        and span.metadata.get("approval") not in {"rejected", "corrected"}
    ]
    if not verifications:
        return None
    last = verifications[-1]
    passed = last.metadata.get("returncode") == 0
    command = str(last.input.get("command", ""))[:120]
    return Score(
        trace.trace_id,
        "verification",
        1.0 if passed else 0.0,
        "verifier",
        f"{command} -> {'pass' if passed else 'fail'}",
    )


def outcome_score(trace: Trace, scores: list[Score]) -> Score:
    by_name = {score.name: score for score in scores}
    chosen = by_name.get("verification") or by_name["turn_signal"]
    return Score(trace.trace_id, "outcome", chosen.value, chosen.source, f"from {chosen.name}: {chosen.comment}")


def score_finished_trace(trace: Trace) -> list[Score]:
    """Immediate scores for a just-finished trace (appended to ``trace.scores``)."""
    scores = [turn_signal_score(trace)]
    verification = verification_score(trace)
    if verification:
        scores.append(verification)
    scores.append(outcome_score(trace, scores))
    trace.scores.extend(scores)
    return scores


def classify_followup(message: str) -> float | None:
    """1.0 when the next user message accepts or continues, 0.0 when it corrects; None when unclear."""
    text = message.strip()
    if not text:
        return None
    corrected = bool(_CORRECTION.search(text))
    accepted = bool(_ACCEPTANCE.search(text))
    if corrected and not accepted:
        return 0.0
    if accepted and not corrected:
        return 1.0
    return None


def followup_score(previous_trace_id: str, message: str) -> Score | None:
    value = classify_followup(message)
    if value is None:
        return None
    comment = "next message corrects the previous turn" if value == 0.0 else "next message accepts or continues"
    return Score(previous_trace_id, "user_followup", value, "heuristic", comment)

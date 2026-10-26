"""Headless eval runs through the product's real chat pipeline.

`run_case` creates a sandbox, builds a `ServerState` on it, and drives `run_turn` with an
`AutoApprovalPolicy` limited to the case's allowed commands: the same prompt assembly, Skills,
memory recall, permission gate and tool execution as the desktop app, with no UI. Afterwards the
case's acceptance script decides pass or fail, and the run's trace (spans and scores) is returned
with an ``eval`` score added. The inherited `run/benchmarks/swebench.py` drives the mini agent
path instead and does not measure these product layers.

``model_factory`` lets tests replace the LLM with a scripted model; real runs use the user's
configured model profile.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vera_agent.evals.cases import EvalCase
from vera_agent.evals.profile import AgentProfile, apply_profile_to_prompt
from vera_agent.evals.sandbox import EVAL_PERMISSIONS, create_sandbox, run_acceptance
from vera_agent.server.chat.control import AutoApprovalPolicy, TurnControl
from vera_agent.server.chat.turn import run_turn
from vera_agent.server.chat.turn_setup import prepare_turn
from vera_agent.server.state import ServerState
from vera_agent.telemetry.recorder import attach_turn_tracer
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Score, Trace

logger = logging.getLogger("vera_eval")

TURN_TIMEOUT_SECONDS = 900


@dataclass
class CaseResult:
    case_id: str
    split: str
    profile_id: str
    repeat: int
    passed: bool
    exit_status: str
    steps: int = 0
    cost: float = 0.0
    duration: float = 0.0
    trace_id: str = ""
    acceptance_output: str = ""
    error: str = ""
    approvals: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] | None = None

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        value = {key: getattr(self, key) for key in self.__dataclass_fields__ if key != "trace"}
        if include_trace:
            value["trace"] = self.trace
        return value


def _seed_profile_memories(state: ServerState, workspace_project_id: str, profile: AgentProfile) -> None:
    if not profile.memories:
        return
    from vera_agent.memory.service import memory_service_for_state

    service = memory_service_for_state(state)
    for item in profile.memories:
        scope = str(item.get("scope") or "user")
        service.add(
            scope=scope,
            scope_id=workspace_project_id if scope == "project" else "",
            kind=str(item.get("kind") or "preference"),
            content=str(item.get("content") or ""),
            source="profile",
        )


async def _drive_turn(state: ServerState, case: EvalCase, profile: AgentProfile, project_id: str, model_id: str):
    policy = AutoApprovalPolicy(command_allowlist=list(case.allowed_commands))
    thread_id = f"eval_{case.case_id}_{uuid.uuid4().hex[:8]}"
    body = {
        "thread_id": thread_id,
        "project_id": project_id,
        "content": case.task,
        "model_id": model_id,
        "attached_skills": sorted(profile.skills),
    }
    ctx = prepare_turn(
        state,
        body,
        approval_policy=policy,
        control=TurnControl.standalone(thread_id),
        permissions_override=EVAL_PERMISSIONS,
        prompt_extender=lambda prompt, prompt_vars, _session: apply_profile_to_prompt(prompt, prompt_vars, profile),
    )
    ctx.tool_call_budget["limit"] = min(ctx.tool_call_limit, case.max_tool_calls)
    ctx.tool_call_limit = ctx.tool_call_budget["limit"]
    finished: list[Trace] = []
    attach_turn_tracer(ctx, on_finish=[finished.append])
    if ctx.tracer:
        ctx.tracer.trace.profile_id = profile.profile_id
        ctx.tracer.trace.task_type = f"eval:{case.split}"
        ctx.tracer.trace.metadata["case_id"] = case.case_id
    async for _event in run_turn(ctx):
        pass
    return ctx, policy, finished[0] if finished else None


def _eval_score(trace: Trace, passed: bool, case: EvalCase) -> Score:
    return Score(trace.trace_id, "eval_accept", 1.0 if passed else 0.0, "eval", f"{case.case_id}: {case.accept[:80]}")


def run_case(
    case: EvalCase,
    profile: AgentProfile,
    models_config: dict[str, Any],
    model_id: str,
    *,
    repeat: int = 0,
    model_factory: Callable[[], Any] | None = None,
    keep_sandbox: bool = False,
) -> CaseResult:
    """Run one case once with ``profile``; never raises for agent or acceptance failures."""
    sandbox = create_sandbox(case, profile, models_config)
    started = time.time()
    result = CaseResult(case.case_id, case.split, profile.profile_id, repeat, passed=False, exit_status="error")
    try:
        state = ServerState(repo_root=sandbox.config_root)
        project_id = f"eval_{case.case_id}"
        state.init_workspace(sandbox.workspace, project_id=project_id, project_name=case.case_id)
        _seed_profile_memories(state, project_id, profile)
        patch = model_factory() if model_factory else None
        if patch is not None:
            patch.start()
        try:
            ctx, policy, trace = asyncio.run(
                asyncio.wait_for(_drive_turn(state, case, profile, project_id, model_id), TURN_TIMEOUT_SECONDS)
            )
        finally:
            if patch is not None:
                patch.stop()
        acceptance = run_acceptance(sandbox, case)
        result.passed = acceptance["passed"]
        result.acceptance_output = acceptance["output"]
        result.approvals = policy.decisions
        if trace is not None:
            score = _eval_score(trace, result.passed, case)
            trace.scores.append(score)
            TraceStore.for_state(state).add_score(score)
            result.trace = trace.to_dict()
            result.trace_id, result.exit_status = trace.trace_id, trace.exit_status
            result.steps, result.cost = trace.steps, trace.cost
    except Exception as error:
        logger.exception("Eval case %s failed to run", case.case_id)
        result.error = f"{type(error).__name__}: {error}"
    finally:
        result.duration = round(time.time() - started, 2)
        if not keep_sandbox:
            sandbox.cleanup()
    return result


def run_suite(
    cases: list[EvalCase],
    profiles: list[AgentProfile],
    models_config: dict[str, Any],
    model_id: str,
    *,
    repeats: int = 1,
    model_factory: Callable[[EvalCase, AgentProfile, int], Any] | None = None,
    on_result: Callable[[CaseResult], None] | None = None,
) -> list[CaseResult]:
    """Run every case ``repeats`` times per profile; results are in (case, repeat, profile) order.

    Interleaving profiles per case keeps model drift during a long run from favouring one side.
    """
    results = []
    for case in cases:
        for repeat in range(repeats):
            for profile in profiles:
                factory = (lambda c=case, p=profile, r=repeat: model_factory(c, p, r)) if model_factory else None
                result = run_case(case, profile, models_config, model_id, repeat=repeat, model_factory=factory)
                results.append(result)
                if on_result:
                    on_result(result)
    return results

"""Evolution proposal routes for the review page.

Routes:
- GET /api/evolution/proposals: proposals, newest first (query: status)
- GET /api/evolution/proposals/{proposal_id}: one proposal with its diff and gate result
- POST /api/evolution/analyze: Critic pass over recent low-score traces (calls the Critic model)
- POST /api/evolution/proposals/{proposal_id}/gate: start the eval gate in the background
- POST /api/evolution/proposals/{proposal_id}/adopt: adopt (body: confirm true, override)
- POST /api/evolution/proposals/{proposal_id}/reject: reject a proposal
- POST /api/evolution/proposals/{proposal_id}/rollback: roll back an adopted proposal
- POST /api/evolution/monitor: compare online outcomes before and after each adoption
- GET /api/evolution/drafts: eval case drafts from low-score traces
- POST /api/evolution/drafts/{trace_id}: save a completed draft as a project eval case

Analyze and gate call the configured models and cost money; nothing here runs on a timer.
Adoption requires ``{"confirm": true}`` in the body so a stray request cannot adopt a proposal.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.evals.cases import EvalCaseError
from vera_agent.evolution.adoption import AdoptionError, adopt, rollback
from vera_agent.evolution.case_drafts import list_drafts, save_draft_as_case
from vera_agent.evolution.engine import analyze_recent, gate_proposal
from vera_agent.evolution.monitor import check_adoptions
from vera_agent.evolution.proposals import ProposalStore
from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.evolution")
_RUNNING_GATES: set[str] = set()
_GATE_LOCK = threading.Lock()


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _proposal_payload(state: ServerState, proposal) -> dict:
    value = proposal.to_dict()
    value["gate_running"] = proposal.proposal_id in _RUNNING_GATES
    diff = ProposalStore.for_state(state).directory / proposal.proposal_id / "diff.md"
    value["diff"] = diff.read_text(encoding="utf-8") if diff.is_file() else proposal.render_diff()
    return value


async def list_proposals(request: Request) -> JSONResponse:
    state = _get_state(request)
    proposals = ProposalStore.for_state(state).list(status=request.query_params.get("status") or None)
    return JSONResponse({"proposals": [_proposal_payload(state, item) for item in proposals]})


async def get_proposal(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        proposal = ProposalStore.for_state(state).get(request.path_params["proposal_id"])
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    return JSONResponse({"proposal": _proposal_payload(state, proposal)})


async def analyze(request: Request) -> JSONResponse:
    try:
        result = await asyncio.to_thread(analyze_recent, _get_state(request))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse(result)


async def start_gate(request: Request) -> JSONResponse:
    state = _get_state(request)
    proposal_id = request.path_params["proposal_id"]
    try:
        proposal = ProposalStore.for_state(state).get(proposal_id)
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    if proposal.kind == "eval_case":
        return JSONResponse({"error": "Eval case proposals are reviewed by the user, not gated."}, status_code=400)
    with _GATE_LOCK:
        if proposal_id in _RUNNING_GATES:
            return JSONResponse({"error": "The gate is already running for this proposal."}, status_code=409)
        _RUNNING_GATES.add(proposal_id)

    def work() -> None:
        try:
            gate_proposal(state, proposal_id)
        except Exception:
            logger.exception("Eval gate failed for %s", proposal_id)
        finally:
            _RUNNING_GATES.discard(proposal_id)

    threading.Thread(target=work, name=f"gate-{proposal_id}", daemon=True).start()
    return JSONResponse({"status": "started", "proposal_id": proposal_id}, status_code=202)


async def adopt_proposal(request: Request) -> JSONResponse:
    state = _get_state(request)
    body = await _body(request)
    if body.get("confirm") is not True:
        return JSONResponse({"error": 'Adoption needs {"confirm": true}.'}, status_code=400)
    try:
        proposal = adopt(
            state,
            ProposalStore.for_state(state),
            request.path_params["proposal_id"],
            override=body.get("override") is True,
        )
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except AdoptionError as error:
        return JSONResponse({"error": str(error)}, status_code=409)
    return JSONResponse({"proposal": _proposal_payload(state, proposal)})


async def reject_proposal(request: Request) -> JSONResponse:
    state = _get_state(request)
    store = ProposalStore.for_state(state)
    try:
        proposal = store.get(request.path_params["proposal_id"])
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    if proposal.status in {"adopted", "rolled_back"}:
        return JSONResponse({"error": "Roll back an adopted proposal instead of rejecting it."}, status_code=409)
    proposal.status = "rejected"
    return JSONResponse({"proposal": _proposal_payload(state, store.save(proposal))})


async def rollback_proposal(request: Request) -> JSONResponse:
    state = _get_state(request)
    body = await _body(request)
    try:
        proposal = rollback(
            state,
            ProposalStore.for_state(state),
            request.path_params["proposal_id"],
            str(body.get("reason") or "rolled back by the user")[:300],
        )
    except LookupError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except AdoptionError as error:
        return JSONResponse({"error": str(error)}, status_code=409)
    return JSONResponse({"proposal": _proposal_payload(state, proposal)})


async def run_monitor(request: Request) -> JSONResponse:
    return JSONResponse({"reports": check_adoptions(_get_state(request))})


async def get_drafts(request: Request) -> JSONResponse:
    return JSONResponse({"drafts": list_drafts(_get_state(request).projects_config_root)})


async def save_draft(request: Request) -> JSONResponse:
    body = await _body(request)
    case = body.get("case")
    if not isinstance(case, dict):
        return JSONResponse({"error": "case (object) is required."}, status_code=400)
    try:
        path = save_draft_as_case(_get_state(request).projects_config_root, request.path_params["trace_id"], case)
    except EvalCaseError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"path": str(path)}, status_code=201)


evolution_routes = [
    Route("/api/evolution/proposals", list_proposals, methods=["GET"]),
    Route("/api/evolution/proposals/{proposal_id}", get_proposal, methods=["GET"]),
    Route("/api/evolution/analyze", analyze, methods=["POST"]),
    Route("/api/evolution/proposals/{proposal_id}/gate", start_gate, methods=["POST"]),
    Route("/api/evolution/proposals/{proposal_id}/adopt", adopt_proposal, methods=["POST"]),
    Route("/api/evolution/proposals/{proposal_id}/reject", reject_proposal, methods=["POST"]),
    Route("/api/evolution/proposals/{proposal_id}/rollback", rollback_proposal, methods=["POST"]),
    Route("/api/evolution/monitor", run_monitor, methods=["POST"]),
    Route("/api/evolution/drafts", get_drafts, methods=["GET"]),
    Route("/api/evolution/drafts/{trace_id}", save_draft, methods=["POST"]),
]

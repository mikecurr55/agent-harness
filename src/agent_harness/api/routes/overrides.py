"""Override endpoints — view and respond to human-in-the-loop approval requests."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_harness.api.state import AppState
from agent_harness.control.override import OverrideDecision

router = APIRouter()


class RespondRequest(BaseModel):
    decision: str  # "approve", "reject", "modify"
    decided_by: str
    modification: str | None = None


@router.get("")
async def list_pending_overrides():
    pending = []
    for session in AppState.sessions.values():
        for req in session.override.pending_requests:
            pending.append({
                "request_id": req.request_id,
                "session_id": session.session_id,
                "agent_id": req.agent_id,
                "action": req.action,
                "resource": req.resource,
                "reason": req.reason,
                "context": req.context,
                "timestamp": req.timestamp.isoformat(),
            })
    return pending


@router.post("/{request_id}/respond")
async def respond_to_override(request_id: str, body: RespondRequest):
    for session in AppState.sessions.values():
        try:
            decision = OverrideDecision(body.decision)
            session.override.respond(
                request_id=request_id,
                decision=decision,
                decided_by=body.decided_by,
                modification=body.modification,
            )
            return {"status": "responded", "decision": body.decision}
        except KeyError:
            continue
    raise HTTPException(404, "Override request not found")

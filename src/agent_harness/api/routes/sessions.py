"""Session management endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_harness.api.state import AppState
from agent_harness.authorization import OperationLimits
from agent_harness.identity import HumanPrincipal

router = APIRouter()


class CreateSessionRequest(BaseModel):
    principal_subject: str
    scopes: list[str]
    max_tool_calls: int = 100
    max_llm_calls: int = 50
    max_dollar_spend: str = "10.00"
    credential_ttl_minutes: int = 15


@router.get("")
async def list_sessions():
    result = []
    for sid, session in AppState.sessions.items():
        result.append(_session_summary(session))
    return result


@router.post("")
async def create_session(req: CreateSessionRequest):
    from agent_harness.orchestration.session import AgentSession

    principal = HumanPrincipal(external_subject=req.principal_subject)
    limits = OperationLimits(
        max_tool_calls=req.max_tool_calls,
        max_llm_calls=req.max_llm_calls,
        max_dollar_spend=req.max_dollar_spend,
    )
    session = AgentSession(
        principal=principal,
        scopes=req.scopes,
        limits=limits,
        credential_ttl=timedelta(minutes=req.credential_ttl_minutes),
    )
    await session.initialize()
    AppState.register_session(session)
    return _session_summary(session)


@router.get("/{session_id}")
async def get_session(session_id: str):
    session = AppState.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return _session_detail(session)


@router.post("/{session_id}/kill")
async def kill_session(session_id: str, reason: str = "Manual operator kill"):
    session = AppState.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session.kill(reason)
    return {"status": "killed", "session_id": session_id}


def _session_summary(session) -> dict:
    killed = session._kill_switch.is_killed
    cred = session.credential
    return {
        "session_id": session.session_id,
        "agent_id": session.agent_id,
        "principal": session.principal.external_subject,
        "scopes": session.scopes,
        "status": "killed" if killed else "active",
        "credential_valid": cred.is_valid if cred else False,
        "credential_expires": cred.expires_at.isoformat() if cred else None,
    }


def _session_detail(session) -> dict:
    summary = _session_summary(session)
    tracker = None
    chain = session.delegation_chain
    summary.update({
        "limits": session.limits.to_dict(),
        "delegation_chain": [
            {
                "delegator": link.delegator_id,
                "delegate": link.delegate_id,
                "scopes": link.scopes,
                "timestamp": link.timestamp.isoformat(),
                "hash": link.hash[:12],
            }
            for link in chain.links
        ] if chain else [],
        "pending_overrides": [
            {
                "request_id": r.request_id,
                "action": r.action,
                "resource": r.resource,
                "reason": r.reason,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in session.override.pending_requests
        ],
    })
    return summary

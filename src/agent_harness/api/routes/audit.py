"""Audit trail endpoints — explore and verify the tamper-evident log."""

from __future__ import annotations

from fastapi import APIRouter, Query

from agent_harness.api.state import AppState

router = APIRouter()


@router.get("")
async def list_audit_entries(
    session_id: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    if session_id:
        entries = await AppState.audit_trail.query_by_session(session_id)
    else:
        entries = await AppState.audit_trail.query_by_session("")
        # Fallback: return all if no session filter (we'll query broadly)
        from sqlalchemy import select
        from agent_harness.audit.models import AuditRecord, AuditEventType, AuditEntry
        async with AppState.audit_trail._session_factory() as db_session:
            query = select(AuditRecord).order_by(AuditRecord.timestamp.desc()).limit(limit)
            if event_type:
                query = query.where(AuditRecord.event_type == event_type)
            result = await db_session.execute(query)
            records = result.scalars().all()
        entries = [
            {
                "entry_id": r.entry_id,
                "timestamp": r.timestamp.isoformat(),
                "event_type": r.event_type,
                "agent_id": r.agent_id,
                "principal_id": r.principal_id,
                "session_id": r.session_id,
                "action": r.action,
                "resource": r.resource,
                "detail": r.detail,
                "entry_hash": r.entry_hash[:16],
                "previous_hash": r.previous_hash[:16] if r.previous_hash else "",
            }
            for r in records
        ]
        return entries

    return [
        {
            "entry_id": e.entry_id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type.value,
            "agent_id": e.agent_id,
            "session_id": e.session_id,
            "action": e.action,
            "resource": e.resource,
            "detail": e.detail,
            "entry_hash": e.entry_hash[:16],
            "previous_hash": e.previous_hash[:16] if e.previous_hash else "",
        }
        for e in entries[:limit]
    ]


@router.get("/verify")
async def verify_audit(session_id: str | None = Query(None)):
    valid, count = await AppState.audit_trail.verify_chain(session_id=session_id)
    return {"valid": valid, "entries_checked": count}


@router.get("/design-changes")
async def list_design_changes():
    return [
        {
            "change_id": c.change_id,
            "timestamp": c.timestamp.isoformat(),
            "change_type": c.change_type.value,
            "changed_by": c.changed_by,
            "component": c.component,
            "reason": c.reason,
            "change_hash": c.change_hash[:16],
        }
        for c in AppState.design_log.entries
    ]

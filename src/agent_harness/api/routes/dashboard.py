"""Dashboard overview endpoint — aggregate stats for the UI home page."""

from __future__ import annotations

from fastapi import APIRouter

from agent_harness.api.state import AppState

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    sessions = AppState.sessions
    active = [s for s in sessions.values() if not s._kill_switch.is_killed]
    killed = [s for s in sessions.values() if s._kill_switch.is_killed]

    pending_overrides = []
    for s in sessions.values():
        pending_overrides.extend(s.override.pending_requests)

    valid, audit_count = await AppState.audit_trail.verify_chain()
    design_valid, design_count = AppState.design_log.verify_chain()

    return {
        "total_sessions": len(sessions),
        "active_sessions": len(active),
        "killed_sessions": len(killed),
        "pending_overrides": len(pending_overrides),
        "audit_entries": audit_count,
        "audit_chain_valid": valid,
        "design_changes": design_count,
        "design_chain_valid": design_valid,
        "policy_rules": len(AppState.policy_engine._rules),
    }

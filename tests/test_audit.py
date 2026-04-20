"""Tests for the tamper-evident audit trail."""

import pytest

from agent_harness.audit import AuditEntry, AuditEventType, AuditTrail


@pytest.fixture
async def trail(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_audit.db'}"
    t = AuditTrail(db_url=db_url)
    await t.initialize()
    return t


async def test_append_and_verify(trail):
    for i in range(5):
        await trail.append(
            AuditEntry(
                event_type=AuditEventType.ACTION_COMPLETED,
                agent_id="agent-1",
                session_id="session-1",
                action=f"step-{i}",
            )
        )
    valid, count = await trail.verify_chain(session_id="session-1")
    assert valid
    assert count == 5


async def test_query_by_session(trail):
    await trail.append(
        AuditEntry(
            event_type=AuditEventType.AGENT_CREATED,
            agent_id="agent-1",
            session_id="session-A",
        )
    )
    await trail.append(
        AuditEntry(
            event_type=AuditEventType.AGENT_CREATED,
            agent_id="agent-2",
            session_id="session-B",
        )
    )
    entries = await trail.query_by_session("session-A")
    assert len(entries) == 1
    assert entries[0].agent_id == "agent-1"

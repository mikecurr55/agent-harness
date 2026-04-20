"""Tamper-evident audit trail — append-only, hash-chained, with async DB persistence."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent_harness.audit.models import AuditEntry, AuditEventType, AuditRecord, Base
from agent_harness.config import settings

logger = structlog.get_logger(__name__)


class AuditTrail:
    """Append-only audit log with hash chaining for tamper evidence.

    Every entry's hash covers the previous entry's hash, so any modification
    or deletion breaks the chain.  Verification walks the chain and re-computes.
    """

    def __init__(self, db_url: str | None = None) -> None:
        url = db_url or settings.audit_db_url
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._last_hash: str = ""

    async def initialize(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditRecord.entry_hash)
                .order_by(AuditRecord.timestamp.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            self._last_hash = row or ""
        logger.info("audit_trail.initialized", last_hash=self._last_hash[:12])

    async def append(self, entry: AuditEntry) -> AuditEntry:
        entry.seal(self._last_hash)
        self._last_hash = entry.entry_hash

        record = AuditRecord(
            entry_id=entry.entry_id,
            timestamp=entry.timestamp,
            event_type=entry.event_type.value,
            agent_id=entry.agent_id,
            principal_id=entry.principal_id,
            session_id=entry.session_id,
            action=entry.action,
            resource=entry.resource,
            detail=entry.detail,
            input_hash=entry.input_hash,
            output_hash=entry.output_hash,
            policy_decision_id=entry.policy_decision_id,
            plan_id=entry.plan_id,
            previous_hash=entry.previous_hash,
            entry_hash=entry.entry_hash,
        )
        async with self._session_factory() as session:
            session.add(record)
            await session.commit()

        logger.debug(
            "audit_trail.appended",
            entry_id=entry.entry_id,
            event=entry.event_type.value,
            hash=entry.entry_hash[:12],
        )
        return entry

    async def verify_chain(self, session_id: str | None = None) -> tuple[bool, int]:
        """Walk the chain and verify every hash. Returns (valid, count)."""
        async with self._session_factory() as session:
            query = select(AuditRecord).order_by(AuditRecord.timestamp.asc())
            if session_id:
                query = query.where(AuditRecord.session_id == session_id)
            result = await session.execute(query)
            records = result.scalars().all()

        prev_hash = ""
        for i, rec in enumerate(records):
            entry = AuditEntry(
                entry_id=rec.entry_id,
                timestamp=rec.timestamp,
                event_type=AuditEventType(rec.event_type),
                agent_id=rec.agent_id,
                principal_id=rec.principal_id,
                session_id=rec.session_id,
                action=rec.action,
                resource=rec.resource,
                detail=rec.detail,
                input_hash=rec.input_hash,
                output_hash=rec.output_hash,
                previous_hash=rec.previous_hash,
                entry_hash=rec.entry_hash,
            )
            expected = entry.compute_hash()
            if entry.entry_hash != expected:
                logger.error("audit_trail.tamper_detected", index=i, entry_id=rec.entry_id)
                return False, i
            if entry.previous_hash != prev_hash:
                logger.error("audit_trail.chain_broken", index=i, entry_id=rec.entry_id)
                return False, i
            prev_hash = entry.entry_hash

        return True, len(records)

    async def query_by_session(self, session_id: str) -> list[AuditEntry]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditRecord)
                .where(AuditRecord.session_id == session_id)
                .order_by(AuditRecord.timestamp.asc())
            )
            records = result.scalars().all()
        return [
            AuditEntry(
                entry_id=r.entry_id,
                timestamp=r.timestamp,
                event_type=AuditEventType(r.event_type),
                agent_id=r.agent_id,
                principal_id=r.principal_id,
                session_id=r.session_id,
                action=r.action,
                resource=r.resource,
                detail=r.detail,
                input_hash=r.input_hash,
                output_hash=r.output_hash,
                previous_hash=r.previous_hash,
                entry_hash=r.entry_hash,
            )
            for r in records
        ]

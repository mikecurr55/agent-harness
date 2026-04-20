"""Audit data models backed by SQLAlchemy for persistent, queryable storage."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase


class AuditEventType(str, Enum):
    AGENT_CREATED = "agent_created"
    CREDENTIAL_ISSUED = "credential_issued"
    CREDENTIAL_REVOKED = "credential_revoked"
    DELEGATION = "delegation"
    PLAN_CREATED = "plan_created"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_DENIED = "policy_denied"
    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    PROMPT = "prompt"
    DEVIATION_DETECTED = "deviation_detected"
    HUMAN_OVERRIDE = "human_override"
    KILL_SWITCH = "kill_switch"
    LIMIT_EXCEEDED = "limit_exceeded"
    DESIGN_CHANGE = "design_change"


class AuditEntry(BaseModel):
    """Immutable audit record. Each entry's hash covers the previous entry's hash,
    forming a tamper-evident chain."""

    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventType
    agent_id: str = ""
    principal_id: str = ""
    session_id: str = ""
    action: str = ""
    resource: str = ""
    detail: str = ""
    input_hash: str = ""
    output_hash: str = ""
    policy_decision_id: str = ""
    plan_id: str = ""
    previous_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        content = (
            f"{self.entry_id}|{self.timestamp.isoformat()}|{self.event_type.value}|"
            f"{self.agent_id}|{self.action}|{self.resource}|{self.detail}|"
            f"{self.input_hash}|{self.output_hash}|{self.previous_hash}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def seal(self, previous_hash: str = "") -> None:
        self.previous_hash = previous_hash
        self.entry_hash = self.compute_hash()


# SQLAlchemy table for persistent audit storage

class Base(DeclarativeBase):
    pass


class AuditRecord(Base):
    __tablename__ = "audit_trail"

    entry_id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    principal_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    action = Column(String(200), nullable=False, default="")
    resource = Column(String(200), nullable=False, default="")
    detail = Column(Text, nullable=False, default="")
    input_hash = Column(String(64), nullable=False, default="")
    output_hash = Column(String(64), nullable=False, default="")
    policy_decision_id = Column(String(36), nullable=False, default="")
    plan_id = Column(String(36), nullable=False, default="")
    previous_hash = Column(String(64), nullable=False, default="")
    entry_hash = Column(String(64), nullable=False, unique=True)

    __table_args__ = (
        Index("ix_audit_session_time", "session_id", "timestamp"),
    )

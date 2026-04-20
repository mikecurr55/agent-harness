"""Tamper-evident audit trail — immutable, hash-chained log of all agent activity."""

from agent_harness.audit.models import AuditEntry, AuditEventType
from agent_harness.audit.trail import AuditTrail

__all__ = ["AuditEntry", "AuditEventType", "AuditTrail"]

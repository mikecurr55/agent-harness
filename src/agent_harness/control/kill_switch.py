"""Kill switch — operators can halt agent execution mid-action."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class KillReason(str, Enum):
    OPERATOR_MANUAL = "operator_manual"
    POLICY_VIOLATION = "policy_violation"
    LIMIT_EXCEEDED = "limit_exceeded"
    DEVIATION_DETECTED = "deviation_detected"
    EVALUATION_FAILED = "evaluation_failed"
    SYSTEM_ERROR = "system_error"


class KillEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: KillReason
    triggered_by: str
    agent_id: str
    session_id: str
    detail: str = ""


class KillSwitch:
    """Cooperative kill switch checked at every action boundary.

    The agent's execution loop checks `is_killed` before each step.
    When triggered, in-flight operations are given a grace window to
    complete before forceful termination.
    """

    def __init__(self) -> None:
        self._killed = asyncio.Event()
        self._events: list[KillEvent] = []

    @property
    def is_killed(self) -> bool:
        return self._killed.is_set()

    @property
    def events(self) -> list[KillEvent]:
        return list(self._events)

    def trigger(
        self,
        reason: KillReason,
        triggered_by: str,
        agent_id: str,
        session_id: str,
        detail: str = "",
    ) -> KillEvent:
        event = KillEvent(
            reason=reason,
            triggered_by=triggered_by,
            agent_id=agent_id,
            session_id=session_id,
            detail=detail,
        )
        self._events.append(event)
        self._killed.set()
        logger.critical(
            "kill_switch.triggered",
            reason=reason.value,
            agent_id=agent_id,
            triggered_by=triggered_by,
            detail=detail,
        )
        return event

    def check_or_raise(self) -> None:
        """Called at every action boundary. Raises if killed."""
        if self._killed.is_set():
            last = self._events[-1] if self._events else None
            reason = last.reason.value if last else "unknown"
            raise AgentKilledError(
                f"Agent execution halted by kill switch: {reason}",
                event=last,
            )

    def reset(self) -> None:
        """Reset after a kill (e.g. for restart under new session)."""
        self._killed.clear()
        logger.info("kill_switch.reset")


class AgentKilledError(Exception):
    """Raised when the kill switch has been triggered."""

    def __init__(self, message: str, event: KillEvent | None = None) -> None:
        self.event = event
        super().__init__(message)

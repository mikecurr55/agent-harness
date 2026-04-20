"""Human override — any decision can be overridden by an authorized human."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class OverrideDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class OverrideRequest(BaseModel):
    """A pending request for human approval."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str
    session_id: str
    action: str
    resource: str
    reason: str
    context: dict[str, str] = Field(default_factory=dict)
    decision: OverrideDecision | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    modification: str | None = None


class HumanOverride:
    """Manages the human-in-the-loop approval flow.

    When the agent encounters a situation requiring human approval (policy
    ESCALATE, plan deviation, evaluation failure), it submits an OverrideRequest
    and blocks until the human responds.

    In production this would integrate with a webhook, Slack, or dashboard.
    Here we use an asyncio.Event for the blocking mechanism.
    """

    def __init__(self) -> None:
        self._pending: dict[str, tuple[OverrideRequest, asyncio.Event]] = {}

    @property
    def pending_requests(self) -> list[OverrideRequest]:
        return [req for req, _ in self._pending.values()]

    async def request_approval(
        self,
        agent_id: str,
        session_id: str,
        action: str,
        resource: str,
        reason: str,
        timeout_seconds: float = 300,
        context: dict[str, str] | None = None,
    ) -> OverrideRequest:
        """Submit a request and block until a human responds or timeout."""
        req = OverrideRequest(
            agent_id=agent_id,
            session_id=session_id,
            action=action,
            resource=resource,
            reason=reason,
            context=context or {},
        )
        event = asyncio.Event()
        self._pending[req.request_id] = (req, event)

        logger.info(
            "override.approval_requested",
            request_id=req.request_id,
            action=action,
            reason=reason,
        )

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            req.decision = OverrideDecision.REJECT
            req.decided_by = "__timeout__"
            req.decided_at = datetime.now(timezone.utc)
            logger.warning("override.timed_out", request_id=req.request_id)
        finally:
            self._pending.pop(req.request_id, None)

        if req.decision == OverrideDecision.REJECT:
            raise OverrideRejectedError(req)

        return req

    def respond(
        self,
        request_id: str,
        decision: OverrideDecision,
        decided_by: str,
        modification: str | None = None,
    ) -> None:
        """Human responds to a pending request."""
        if request_id not in self._pending:
            raise KeyError(f"No pending request with id {request_id}")

        req, event = self._pending[request_id]
        req.decision = decision
        req.decided_by = decided_by
        req.decided_at = datetime.now(timezone.utc)
        req.modification = modification
        event.set()

        logger.info(
            "override.response_received",
            request_id=request_id,
            decision=decision.value,
            decided_by=decided_by,
        )


class OverrideRejectedError(Exception):
    def __init__(self, request: OverrideRequest) -> None:
        self.request = request
        super().__init__(
            f"Human override rejected: {request.action} on {request.resource} — {request.reason}"
        )

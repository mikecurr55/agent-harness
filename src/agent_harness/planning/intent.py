"""Intent binding — each runtime action is checked against the approved plan.

Deviations from plan trigger human approval before continuing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from agent_harness.planning.plan import ExecutionPlan

logger = structlog.get_logger(__name__)


class DeviationType(str, Enum):
    UNPLANNED_ACTION = "unplanned_action"
    WRONG_RESOURCE = "wrong_resource"
    OUT_OF_ORDER = "out_of_order"
    PLAN_INTEGRITY_BROKEN = "plan_integrity_broken"


class DeviationResult(BaseModel):
    deviation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    deviation_type: DeviationType
    expected_action: str = ""
    actual_action: str = ""
    expected_resource: str = ""
    actual_resource: str = ""
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requires_human_approval: bool = True


class IntentBinder:
    """Binds runtime actions to the sealed execution plan.

    Every action the agent attempts is compared against the next planned step.
    Mismatches produce a DeviationResult which, by default, requires human
    approval before the agent may continue.
    """

    def __init__(self, plan: ExecutionPlan) -> None:
        self._plan = plan

    def check_action(self, action: str, resource: str) -> DeviationResult | None:
        if not self._plan.integrity_valid:
            return DeviationResult(
                deviation_type=DeviationType.PLAN_INTEGRITY_BROKEN,
                actual_action=action,
                actual_resource=resource,
                message="Plan hash mismatch — the plan may have been tampered with.",
            )

        next_step = self._plan.next_step()
        if next_step is None:
            return DeviationResult(
                deviation_type=DeviationType.UNPLANNED_ACTION,
                actual_action=action,
                actual_resource=resource,
                message="All planned steps completed but agent is still acting.",
            )

        if next_step.action != action:
            return DeviationResult(
                deviation_type=DeviationType.UNPLANNED_ACTION,
                expected_action=next_step.action,
                actual_action=action,
                expected_resource=next_step.resource,
                actual_resource=resource,
                message=f"Expected action '{next_step.action}' but got '{action}'.",
            )

        if next_step.resource != resource and next_step.resource != "*":
            return DeviationResult(
                deviation_type=DeviationType.WRONG_RESOURCE,
                expected_action=next_step.action,
                actual_action=action,
                expected_resource=next_step.resource,
                actual_resource=resource,
                message=f"Action matches but resource differs: expected '{next_step.resource}', got '{resource}'.",
            )

        logger.debug(
            "intent_binder.action_matches_plan",
            step_id=next_step.step_id,
            action=action,
        )
        return None

    def confirm_step(self, step_id: str) -> None:
        """Mark a plan step as completed after successful execution."""
        self._plan.mark_step_complete(step_id)

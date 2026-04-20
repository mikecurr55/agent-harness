"""Execution plan data model — the approved contract for what the agent will do."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    DEVIATED = "deviated"


class PlanStep(BaseModel):
    """A single planned action with its expected tool, resource, and intent."""

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    action: str
    resource: str
    description: str
    required_scopes: list[str] = Field(default_factory=list)
    expected_output_schema: dict | None = None
    completed: bool = False
    completed_at: datetime | None = None


class ExecutionPlan(BaseModel):
    """An ordered, hash-sealed plan binding agent intent to specific actions.

    Once approved, the plan hash is locked. Any modification changes the hash,
    which the IntentBinder will detect as a deviation.
    """

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    principal_id: str
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None
    approved_by: str | None = None
    plan_hash: str = ""

    def compute_hash(self) -> str:
        content = "|".join(
            f"{s.order}:{s.action}:{s.resource}" for s in sorted(self.steps, key=lambda s: s.order)
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def seal(self) -> None:
        """Lock the plan hash after approval."""
        self.plan_hash = self.compute_hash()

    @property
    def is_sealed(self) -> bool:
        return bool(self.plan_hash)

    @property
    def integrity_valid(self) -> bool:
        if not self.plan_hash:
            return True
        return self.compute_hash() == self.plan_hash

    def approve(self, approver_id: str) -> None:
        self.status = PlanStatus.APPROVED
        self.approved_at = datetime.now(timezone.utc)
        self.approved_by = approver_id
        self.seal()

    def next_step(self) -> PlanStep | None:
        for step in sorted(self.steps, key=lambda s: s.order):
            if not step.completed:
                return step
        return None

    def mark_step_complete(self, step_id: str) -> None:
        for step in self.steps:
            if step.step_id == step_id:
                step.completed = True
                step.completed_at = datetime.now(timezone.utc)
                return
        raise ValueError(f"Step {step_id} not found in plan {self.plan_id}")

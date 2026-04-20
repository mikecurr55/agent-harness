"""Operation and dollar limits — hard caps on what an agent can spend or do."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field


class OperationLimits(BaseModel):
    """Declarative limits for an agent session."""

    max_tool_calls: int = 100
    max_llm_calls: int = 50
    max_dollar_spend: Decimal = Decimal("10.00")
    max_records_accessed: int = 1000
    max_wall_clock_seconds: int = 300

    def to_dict(self) -> dict[str, str]:
        return {
            "max_tool_calls": str(self.max_tool_calls),
            "max_llm_calls": str(self.max_llm_calls),
            "max_dollar_spend": str(self.max_dollar_spend),
            "max_records_accessed": str(self.max_records_accessed),
            "max_wall_clock_seconds": str(self.max_wall_clock_seconds),
        }


class LimitTracker(BaseModel):
    """Tracks consumption against limits. Raises when any limit is breached."""

    limits: OperationLimits
    tool_calls: int = 0
    llm_calls: int = 0
    dollar_spend: Decimal = Decimal("0")
    records_accessed: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def record_tool_call(self, cost: Decimal = Decimal("0")) -> None:
        self.tool_calls += 1
        self.dollar_spend += cost
        self._enforce()

    def record_llm_call(self, cost: Decimal = Decimal("0")) -> None:
        self.llm_calls += 1
        self.dollar_spend += cost
        self._enforce()

    def record_data_access(self, count: int = 1) -> None:
        self.records_accessed += count
        self._enforce()

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    @property
    def remaining(self) -> dict[str, str]:
        return {
            "tool_calls": f"{self.limits.max_tool_calls - self.tool_calls}",
            "llm_calls": f"{self.limits.max_llm_calls - self.llm_calls}",
            "dollar_spend": f"{self.limits.max_dollar_spend - self.dollar_spend}",
            "records": f"{self.limits.max_records_accessed - self.records_accessed}",
            "wall_clock": f"{self.limits.max_wall_clock_seconds - self.elapsed_seconds:.0f}s",
        }

    def _enforce(self) -> None:
        violations: list[str] = []
        if self.tool_calls > self.limits.max_tool_calls:
            violations.append(
                f"Tool call limit exceeded ({self.tool_calls}/{self.limits.max_tool_calls})"
            )
        if self.llm_calls > self.limits.max_llm_calls:
            violations.append(
                f"LLM call limit exceeded ({self.llm_calls}/{self.limits.max_llm_calls})"
            )
        if self.dollar_spend > self.limits.max_dollar_spend:
            violations.append(
                f"Dollar limit exceeded (${self.dollar_spend}/${self.limits.max_dollar_spend})"
            )
        if self.records_accessed > self.limits.max_records_accessed:
            violations.append(
                f"Data access limit exceeded ({self.records_accessed}/{self.limits.max_records_accessed})"
            )
        if self.elapsed_seconds > self.limits.max_wall_clock_seconds:
            violations.append(
                f"Wall clock limit exceeded ({self.elapsed_seconds:.0f}s/{self.limits.max_wall_clock_seconds}s)"
            )
        if violations:
            raise ResourceExhaustedError(violations)


class ResourceExhaustedError(Exception):
    """Raised when an agent exceeds one or more operation limits."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"Limit violations: {'; '.join(violations)}")

"""Plan validation — ensures a plan is well-formed and within authorization bounds."""

from __future__ import annotations

from agent_harness.authorization.scopes import AuthorizationContext
from agent_harness.planning.plan import ExecutionPlan, PlanStatus


class PlanValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Plan validation failed: {'; '.join(errors)}")


class PlanValidator:
    """Validates plans before they can be approved."""

    @staticmethod
    def validate(plan: ExecutionPlan, auth_ctx: AuthorizationContext) -> list[str]:
        errors: list[str] = []

        if not plan.steps:
            errors.append("Plan has no steps.")

        if plan.status not in (PlanStatus.DRAFT, PlanStatus.PENDING_APPROVAL):
            errors.append(f"Plan is in non-validatable status: {plan.status.value}")

        orders = [s.order for s in plan.steps]
        if len(orders) != len(set(orders)):
            errors.append("Duplicate step order values.")

        for step in plan.steps:
            for scope in step.required_scopes:
                decision = auth_ctx.check(scope)
                if decision.value == "deny":
                    errors.append(
                        f"Step {step.order} requires scope '{scope}' not granted to agent."
                    )

        return errors

    @staticmethod
    def validate_or_raise(plan: ExecutionPlan, auth_ctx: AuthorizationContext) -> None:
        errors = PlanValidator.validate(plan, auth_ctx)
        if errors:
            raise PlanValidationError(errors)

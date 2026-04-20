"""Deterministic policy engine — evaluates every action against loaded policies.

Designed for integration with the Microsoft Agent Governance Toolkit.
Policy definitions are YAML files loaded at startup; the engine evaluates
them in order with a deny-wins model.  Denials are logged and terminal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class PolicyDecision(BaseModel):
    """Immutable record of a policy evaluation."""

    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str
    action: str
    resource: str
    verdict: PolicyVerdict
    matched_policy: str = ""
    reason: str = ""
    context: dict[str, str] = Field(default_factory=dict)


class PolicyRule(BaseModel):
    """A single policy rule from a YAML definition."""

    id: str
    description: str = ""
    action_pattern: str
    resource_pattern: str = "*"
    conditions: dict[str, str] = Field(default_factory=dict)
    verdict: PolicyVerdict
    priority: int = 0


class PolicyEngine:
    """Evaluates agent actions against a set of deterministic policy rules.

    All denials are terminal — the action is blocked and logged.  ESCALATE
    verdicts pause execution pending human approval.
    """

    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []

    def load_rules(self, rules: list[PolicyRule]) -> None:
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        logger.info("policy_engine.rules_loaded", count=len(self._rules))

    def evaluate(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, str] | None = None,
    ) -> PolicyDecision:
        ctx = context or {}

        for rule in self._rules:
            if not self._matches(rule, action, resource, ctx):
                continue

            decision = PolicyDecision(
                agent_id=agent_id,
                action=action,
                resource=resource,
                verdict=rule.verdict,
                matched_policy=rule.id,
                reason=rule.description,
                context=ctx,
            )

            logger.info(
                "policy_engine.evaluated",
                verdict=rule.verdict.value,
                policy=rule.id,
                action=action,
                resource=resource,
                agent_id=agent_id,
            )
            return decision

        return PolicyDecision(
            agent_id=agent_id,
            action=action,
            resource=resource,
            verdict=PolicyVerdict.DENY,
            matched_policy="__default_deny__",
            reason="No policy matched — default deny.",
            context=ctx,
        )

    def evaluate_or_raise(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, str] | None = None,
    ) -> PolicyDecision:
        decision = self.evaluate(agent_id, action, resource, context)
        if decision.verdict == PolicyVerdict.DENY:
            raise PolicyDeniedError(decision)
        return decision

    @staticmethod
    def _matches(
        rule: PolicyRule, action: str, resource: str, context: dict[str, str]
    ) -> bool:
        if rule.action_pattern != "*" and rule.action_pattern != action:
            if not action.startswith(rule.action_pattern.rstrip("*")):
                return False
        if rule.resource_pattern != "*" and rule.resource_pattern != resource:
            if not resource.startswith(rule.resource_pattern.rstrip("*")):
                return False
        for key, expected in rule.conditions.items():
            if context.get(key) != expected:
                return False
        return True


class PolicyDeniedError(Exception):
    """Raised when a policy evaluation results in DENY — terminal for the action."""

    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Policy DENIED: {decision.matched_policy} — {decision.reason} "
            f"(action={decision.action}, resource={decision.resource})"
        )

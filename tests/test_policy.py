"""Tests for the policy engine."""

from agent_harness.policy.engine import PolicyEngine, PolicyRule, PolicyVerdict, PolicyDeniedError


def _build_engine() -> PolicyEngine:
    engine = PolicyEngine()
    engine.load_rules([
        PolicyRule(
            id="allow-reads",
            action_pattern="tool:read:*",
            verdict=PolicyVerdict.ALLOW,
            priority=10,
        ),
        PolicyRule(
            id="deny-pii",
            action_pattern="*",
            resource_pattern="data:pii:*",
            verdict=PolicyVerdict.DENY,
            priority=100,
        ),
        PolicyRule(
            id="escalate-writes",
            action_pattern="tool:write:*",
            verdict=PolicyVerdict.ESCALATE,
            priority=20,
        ),
    ])
    return engine


def test_policy_allows_reads():
    engine = _build_engine()
    decision = engine.evaluate("agent-1", "tool:read:search", "data:customer")
    assert decision.verdict == PolicyVerdict.ALLOW


def test_policy_denies_pii():
    engine = _build_engine()
    decision = engine.evaluate("agent-1", "tool:read:search", "data:pii:ssn")
    assert decision.verdict == PolicyVerdict.DENY


def test_policy_escalates_writes():
    engine = _build_engine()
    decision = engine.evaluate("agent-1", "tool:write:update", "data:customer")
    assert decision.verdict == PolicyVerdict.ESCALATE


def test_default_deny_on_unknown():
    engine = _build_engine()
    decision = engine.evaluate("agent-1", "unknown:action", "unknown:resource")
    assert decision.verdict == PolicyVerdict.DENY
    assert decision.matched_policy == "__default_deny__"


def test_evaluate_or_raise_on_deny():
    engine = _build_engine()
    try:
        engine.evaluate_or_raise("agent-1", "tool:read:search", "data:pii:ssn")
        assert False, "Should have raised PolicyDeniedError"
    except PolicyDeniedError as exc:
        assert exc.decision.verdict == PolicyVerdict.DENY

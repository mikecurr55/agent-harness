"""Scoped authorization — tools, data domains, and operation limits."""

from agent_harness.authorization.scopes import Scope, ScopeRegistry, AuthorizationContext
from agent_harness.authorization.limits import OperationLimits, LimitTracker

__all__ = [
    "Scope",
    "ScopeRegistry",
    "AuthorizationContext",
    "OperationLimits",
    "LimitTracker",
]

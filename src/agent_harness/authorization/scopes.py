"""Scoped authorization: tools, data domains, and explicit permission grants."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ScopeType(str, Enum):
    TOOL = "tool"
    DATA = "data"
    ACTION = "action"


class Scope(BaseModel):
    """A single permission scope — e.g. tool:search, data:customer_pii, action:deploy."""

    scope_type: ScopeType
    resource: str
    read: bool = True
    write: bool = False
    description: str = ""

    @property
    def key(self) -> str:
        return f"{self.scope_type.value}:{self.resource}"


class ScopeRegistry(BaseModel):
    """Central registry of all available scopes and their constraints."""

    scopes: dict[str, Scope] = Field(default_factory=dict)

    def register(self, scope: Scope) -> None:
        self.scopes[scope.key] = scope

    def resolve(self, scope_keys: list[str]) -> list[Scope]:
        resolved = []
        for key in scope_keys:
            if key not in self.scopes:
                raise KeyError(f"Unknown scope: {key}")
            resolved.append(self.scopes[key])
        return resolved


class AuthorizationDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class AuthorizationContext(BaseModel):
    """Evaluates whether an agent action is within its granted scopes."""

    granted_scopes: set[str] = Field(default_factory=set)

    def check(self, required_scope: str) -> AuthorizationDecision:
        if required_scope in self.granted_scopes:
            return AuthorizationDecision.ALLOW
        return AuthorizationDecision.DENY

    def check_or_raise(self, required_scope: str, action_description: str = "") -> None:
        if self.check(required_scope) == AuthorizationDecision.DENY:
            desc = f" for '{action_description}'" if action_description else ""
            raise PermissionError(
                f"Agent lacks scope '{required_scope}'{desc}. "
                f"Granted: {sorted(self.granted_scopes)}"
            )

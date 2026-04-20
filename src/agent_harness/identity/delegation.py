"""Delegation chain — traceable lineage from human principal through agent instances."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DelegationLink(BaseModel):
    """One hop in the delegation chain: who delegated to whom, with what scopes."""

    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    delegator_id: str
    delegate_id: str
    scopes: list[str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    hash: str = ""

    def model_post_init(self, _context: object) -> None:
        if not self.hash:
            content = (
                f"{self.delegator_id}|{self.delegate_id}|"
                f"{','.join(sorted(self.scopes))}|{self.timestamp.isoformat()}"
            )
            self.hash = hashlib.sha256(content.encode()).hexdigest()


class DelegationChain(BaseModel):
    """Ordered list of delegation links forming a traceable path from principal to agent.

    Each link's hash covers its content; the chain is verifiable by walking
    from root to leaf and checking that scopes only narrow (never widen).
    """

    chain_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    links: list[DelegationLink] = Field(default_factory=list)

    @property
    def root_principal_id(self) -> str | None:
        return self.links[0].delegator_id if self.links else None

    @property
    def current_agent_id(self) -> str | None:
        return self.links[-1].delegate_id if self.links else None

    @property
    def effective_scopes(self) -> set[str]:
        """The active scope set is the intersection of every link's scopes."""
        if not self.links:
            return set()
        scopes = set(self.links[0].scopes)
        for link in self.links[1:]:
            scopes &= set(link.scopes)
        return scopes

    def append(
        self,
        delegator_id: str,
        delegate_id: str,
        scopes: list[str],
        reason: str = "",
    ) -> DelegationLink:
        if self.links:
            allowed = self.effective_scopes
            requested = set(scopes)
            if not requested.issubset(allowed):
                escalated = requested - allowed
                raise PermissionError(
                    f"Scope escalation denied: {escalated} not in parent scopes {allowed}"
                )
        link = DelegationLink(
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            scopes=scopes,
            reason=reason,
        )
        self.links.append(link)
        return link

    def verify_integrity(self) -> bool:
        """Re-compute each link hash and confirm no tampering."""
        for link in self.links:
            content = (
                f"{link.delegator_id}|{link.delegate_id}|"
                f"{','.join(sorted(link.scopes))}|{link.timestamp.isoformat()}"
            )
            expected = hashlib.sha256(content.encode()).hexdigest()
            if link.hash != expected:
                return False
        return True

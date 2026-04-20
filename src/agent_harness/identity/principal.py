"""Human principal binding — the root of every delegation chain."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HumanPrincipal(BaseModel):
    """Represents the authenticated human who spawned the agent session.

    The fingerprint is a SHA-256 over the external identity token, creating a
    stable pseudonymous anchor without storing raw credentials.
    """

    principal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    external_subject: str = Field(
        ..., description="Sub claim or username from the IdP"
    )
    fingerprint: str = Field(
        default="",
        description="SHA-256 of the identity token, set at creation",
    )
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, _context: object) -> None:
        if not self.fingerprint:
            raw = f"{self.external_subject}:{self.authenticated_at.isoformat()}"
            self.fingerprint = hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def from_token(token: str, subject: str) -> HumanPrincipal:
        """Build a principal from an IdP token, hashing the token for the fingerprint."""
        fp = hashlib.sha256(token.encode()).hexdigest()
        return HumanPrincipal(external_subject=subject, fingerprint=fp)

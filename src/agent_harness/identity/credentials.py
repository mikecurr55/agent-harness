"""Short-lived agent credentials — temporal identities bound to a principal."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, Field


class CredentialStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AgentCredential(BaseModel):
    """A short-lived credential issued to a specific agent instance.

    Contains a signed JWT binding the agent_id to the human principal,
    with explicit scopes and a hard TTL.
    """

    credential_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    principal_id: str
    scopes: list[str] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    status: CredentialStatus = CredentialStatus.ACTIVE
    token: str = ""

    @property
    def is_valid(self) -> bool:
        return (
            self.status == CredentialStatus.ACTIVE
            and datetime.now(timezone.utc) < self.expires_at
        )

    def revoke(self) -> None:
        self.status = CredentialStatus.REVOKED


class CredentialManager:
    """Issues and validates short-lived agent credentials.

    Uses ECDSA P-256 for compact, fast signing.  In production the private key
    would live in an HSM or KMS — here we hold it in memory for the session.
    """

    def __init__(self, ttl: timedelta = timedelta(minutes=15)) -> None:
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()
        self._ttl = ttl

    def issue(
        self,
        agent_id: str,
        principal_id: str,
        scopes: list[str],
        ttl_override: timedelta | None = None,
    ) -> AgentCredential:
        now = datetime.now(timezone.utc)
        ttl = ttl_override or self._ttl
        expires = now + ttl
        payload = {
            "sub": agent_id,
            "principal": principal_id,
            "scopes": scopes,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }
        token = jwt.encode(payload, self._private_key, algorithm="ES256")
        return AgentCredential(
            agent_id=agent_id,
            principal_id=principal_id,
            scopes=scopes,
            issued_at=now,
            expires_at=expires,
            token=token,
        )

    def validate(self, token: str) -> dict:
        """Decode and verify a credential token. Raises on invalid/expired."""
        return jwt.decode(token, self._public_key, algorithms=["ES256"])

    def refresh(self, credential: AgentCredential) -> AgentCredential:
        """Revoke the old credential and issue a replacement with the same scopes."""
        credential.revoke()
        return self.issue(
            credential.agent_id,
            credential.principal_id,
            credential.scopes,
        )

"""Tests for the identity layer: principals, credentials, delegation."""

from datetime import timedelta

from agent_harness.identity import (
    CredentialManager,
    DelegationChain,
    HumanPrincipal,
)


def test_principal_fingerprint_is_stable():
    p = HumanPrincipal(external_subject="alice@corp.com")
    assert len(p.fingerprint) == 64
    assert p.principal_id


def test_principal_from_token():
    p = HumanPrincipal.from_token("fake-jwt-token", "alice@corp.com")
    assert p.external_subject == "alice@corp.com"
    assert len(p.fingerprint) == 64


def test_credential_issue_and_validate():
    mgr = CredentialManager(ttl=timedelta(minutes=5))
    cred = mgr.issue("agent-1", "principal-1", ["tool:read:*", "llm:invoke"])
    assert cred.is_valid
    assert cred.token

    payload = mgr.validate(cred.token)
    assert payload["sub"] == "agent-1"
    assert payload["principal"] == "principal-1"
    assert "tool:read:*" in payload["scopes"]


def test_credential_revoke():
    mgr = CredentialManager()
    cred = mgr.issue("agent-1", "principal-1", ["tool:read:*"])
    cred.revoke()
    assert not cred.is_valid


def test_credential_refresh():
    mgr = CredentialManager()
    cred = mgr.issue("agent-1", "principal-1", ["tool:read:*"])
    new_cred = mgr.refresh(cred)
    assert not cred.is_valid
    assert new_cred.is_valid
    assert new_cred.credential_id != cred.credential_id


def test_delegation_chain_scope_narrowing():
    chain = DelegationChain()
    chain.append("principal", "agent-1", ["tool:read:*", "llm:invoke", "data:customer"])
    chain.append("agent-1", "agent-2", ["tool:read:*", "llm:invoke"])
    assert chain.effective_scopes == {"tool:read:*", "llm:invoke"}


def test_delegation_chain_blocks_escalation():
    chain = DelegationChain()
    chain.append("principal", "agent-1", ["tool:read:*"])
    try:
        chain.append("agent-1", "agent-2", ["tool:read:*", "tool:write:deploy"])
        assert False, "Should have raised PermissionError"
    except PermissionError as exc:
        assert "escalation" in str(exc).lower()


def test_delegation_chain_integrity():
    chain = DelegationChain()
    chain.append("principal", "agent-1", ["tool:read:*"])
    chain.append("agent-1", "agent-2", ["tool:read:*"])
    assert chain.verify_integrity()

    chain.links[0].delegator_id = "tampered"
    assert not chain.verify_integrity()

"""Policy management endpoints — view and update policy rules."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_harness.api.state import AppState
from agent_harness.logging.design_log import DesignChange, DesignChangeType
from agent_harness.policy.engine import PolicyRule, PolicyVerdict

router = APIRouter()


class PolicyRuleRequest(BaseModel):
    id: str
    description: str = ""
    action_pattern: str = "*"
    resource_pattern: str = "*"
    conditions: dict[str, str] = {}
    verdict: str = "deny"
    priority: int = 0


@router.get("")
async def list_policies():
    return [
        {
            "id": r.id,
            "description": r.description,
            "action_pattern": r.action_pattern,
            "resource_pattern": r.resource_pattern,
            "conditions": r.conditions,
            "verdict": r.verdict.value,
            "priority": r.priority,
        }
        for r in AppState.policy_engine._rules
    ]


@router.post("")
async def add_policy(body: PolicyRuleRequest):
    existing_ids = {r.id for r in AppState.policy_engine._rules}
    if body.id in existing_ids:
        raise HTTPException(409, f"Policy '{body.id}' already exists. Use PUT to update.")

    rule = PolicyRule(
        id=body.id,
        description=body.description,
        action_pattern=body.action_pattern,
        resource_pattern=body.resource_pattern,
        conditions=body.conditions,
        verdict=PolicyVerdict(body.verdict),
        priority=body.priority,
    )
    rules = list(AppState.policy_engine._rules) + [rule]
    AppState.policy_engine.load_rules(rules)

    AppState.design_log.append(
        DesignChange(
            change_type=DesignChangeType.POLICY_ADDED,
            changed_by="api_user",
            component=f"policy:{body.id}",
            after=body.model_dump(),
            reason=f"Added via UI: {body.description}",
        )
    )

    return {"status": "created", "id": body.id}


@router.put("/{policy_id}")
async def update_policy(policy_id: str, body: PolicyRuleRequest):
    old_rules = list(AppState.policy_engine._rules)
    old_rule = next((r for r in old_rules if r.id == policy_id), None)
    if not old_rule:
        raise HTTPException(404, f"Policy '{policy_id}' not found")

    before = {
        "action_pattern": old_rule.action_pattern,
        "resource_pattern": old_rule.resource_pattern,
        "verdict": old_rule.verdict.value,
        "priority": old_rule.priority,
    }

    new_rule = PolicyRule(
        id=policy_id,
        description=body.description,
        action_pattern=body.action_pattern,
        resource_pattern=body.resource_pattern,
        conditions=body.conditions,
        verdict=PolicyVerdict(body.verdict),
        priority=body.priority,
    )
    updated = [new_rule if r.id == policy_id else r for r in old_rules]
    AppState.policy_engine.load_rules(updated)

    AppState.design_log.append(
        DesignChange(
            change_type=DesignChangeType.POLICY_MODIFIED,
            changed_by="api_user",
            component=f"policy:{policy_id}",
            before=before,
            after=body.model_dump(),
            reason=f"Updated via UI",
        )
    )

    return {"status": "updated", "id": policy_id}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str):
    old_rules = list(AppState.policy_engine._rules)
    rule = next((r for r in old_rules if r.id == policy_id), None)
    if not rule:
        raise HTTPException(404, f"Policy '{policy_id}' not found")

    updated = [r for r in old_rules if r.id != policy_id]
    AppState.policy_engine.load_rules(updated)

    AppState.design_log.append(
        DesignChange(
            change_type=DesignChangeType.POLICY_REMOVED,
            changed_by="api_user",
            component=f"policy:{policy_id}",
            before={"id": policy_id, "description": rule.description},
            reason=f"Deleted via UI",
        )
    )

    return {"status": "deleted", "id": policy_id}

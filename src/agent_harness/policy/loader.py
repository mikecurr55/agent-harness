"""Load policy rules from YAML files — compatible with MS Agent Governance Toolkit format."""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_harness.policy.engine import PolicyRule, PolicyVerdict


class PolicyLoader:
    """Reads YAML policy definitions from a directory and produces PolicyRule objects."""

    @staticmethod
    def load_directory(policy_dir: Path) -> list[PolicyRule]:
        rules: list[PolicyRule] = []
        if not policy_dir.exists():
            return rules
        for path in sorted(policy_dir.glob("*.yaml")):
            rules.extend(PolicyLoader.load_file(path))
        for path in sorted(policy_dir.glob("*.yml")):
            rules.extend(PolicyLoader.load_file(path))
        return rules

    @staticmethod
    def load_file(path: Path) -> list[PolicyRule]:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not data or "policies" not in data:
            return []
        rules: list[PolicyRule] = []
        for entry in data["policies"]:
            rules.append(
                PolicyRule(
                    id=entry["id"],
                    description=entry.get("description", ""),
                    action_pattern=entry.get("action", "*"),
                    resource_pattern=entry.get("resource", "*"),
                    conditions=entry.get("conditions", {}),
                    verdict=PolicyVerdict(entry.get("verdict", "deny")),
                    priority=entry.get("priority", 0),
                )
            )
        return rules

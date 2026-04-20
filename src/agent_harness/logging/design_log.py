"""Design change log — captures all modifications to the orchestration graph,
policies, scopes, and agent configuration.

Every change is hashed and appended to an immutable log, paralleling the
runtime audit trail but focused on configuration-time changes.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class DesignChangeType(str, Enum):
    POLICY_ADDED = "policy_added"
    POLICY_MODIFIED = "policy_modified"
    POLICY_REMOVED = "policy_removed"
    SCOPE_ADDED = "scope_added"
    SCOPE_REMOVED = "scope_removed"
    GRAPH_NODE_ADDED = "graph_node_added"
    GRAPH_NODE_REMOVED = "graph_node_removed"
    GRAPH_EDGE_MODIFIED = "graph_edge_modified"
    LIMIT_CHANGED = "limit_changed"
    TOOL_REGISTERED = "tool_registered"
    TOOL_REMOVED = "tool_removed"
    CONFIG_CHANGED = "config_changed"


class DesignChange(BaseModel):
    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_type: DesignChangeType
    changed_by: str
    component: str
    before: dict | None = None
    after: dict | None = None
    reason: str = ""
    previous_hash: str = ""
    change_hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps(
            {
                "id": self.change_id,
                "ts": self.timestamp.isoformat(),
                "type": self.change_type.value,
                "by": self.changed_by,
                "component": self.component,
                "before": self.before,
                "after": self.after,
                "prev": self.previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def seal(self, previous_hash: str = "") -> None:
        self.previous_hash = previous_hash
        self.change_hash = self.compute_hash()


class DesignChangeLog:
    """Append-only, hash-chained log of all design/configuration changes."""

    def __init__(self) -> None:
        self._entries: list[DesignChange] = []
        self._last_hash: str = ""

    def append(self, change: DesignChange) -> DesignChange:
        change.seal(self._last_hash)
        self._last_hash = change.change_hash
        self._entries.append(change)
        logger.info(
            "design_log.change_recorded",
            change_type=change.change_type.value,
            component=change.component,
            changed_by=change.changed_by,
            hash=change.change_hash[:12],
        )
        return change

    @property
    def entries(self) -> list[DesignChange]:
        return list(self._entries)

    def verify_chain(self) -> tuple[bool, int]:
        prev_hash = ""
        for i, entry in enumerate(self._entries):
            expected = entry.compute_hash()
            if entry.change_hash != expected or entry.previous_hash != prev_hash:
                return False, i
            prev_hash = entry.change_hash
        return True, len(self._entries)

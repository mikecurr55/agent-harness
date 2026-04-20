"""Runtime log — structured capture of all agent activity via structlog."""

from __future__ import annotations

from typing import Any

import structlog


def configure_logging(json_output: bool = True) -> None:
    """Configure structlog for the harness — JSON for production, console for dev."""
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RuntimeLog:
    """Convenience wrapper for runtime activity logging with session context."""

    def __init__(self, agent_id: str, session_id: str) -> None:
        self._log = structlog.get_logger("agent_harness.runtime")
        self._agent_id = agent_id
        self._session_id = session_id

    def _bind(self) -> Any:
        return self._log.bind(agent_id=self._agent_id, session_id=self._session_id)

    def action_start(self, action: str, resource: str, **extra: Any) -> None:
        self._bind().info("action.start", action=action, resource=resource, **extra)

    def action_complete(self, action: str, resource: str, **extra: Any) -> None:
        self._bind().info("action.complete", action=action, resource=resource, **extra)

    def action_error(self, action: str, error: str, **extra: Any) -> None:
        self._bind().error("action.error", action=action, error=error, **extra)

    def policy_check(self, action: str, verdict: str, policy: str, **extra: Any) -> None:
        self._bind().info("policy.check", action=action, verdict=verdict, policy=policy, **extra)

    def credential_event(self, event: str, **extra: Any) -> None:
        self._bind().info("credential.event", event=event, **extra)

    def kill_event(self, reason: str, **extra: Any) -> None:
        self._bind().critical("kill.triggered", reason=reason, **extra)

    def override_event(self, action: str, decision: str, **extra: Any) -> None:
        self._bind().warning("override.decision", action=action, decision=decision, **extra)

"""Shared application state — singleton registry of active sessions and subsystems."""

from __future__ import annotations

from pathlib import Path

from agent_harness.audit import AuditTrail
from agent_harness.config import settings
from agent_harness.control import KillSwitch
from agent_harness.control.override import HumanOverride
from agent_harness.logging.design_log import DesignChangeLog
from agent_harness.observability import OutputEvaluator, TracingManager
from agent_harness.orchestration.session import AgentSession
from agent_harness.policy import PolicyEngine, PolicyLoader


class AppState:
    """Singleton holding all shared subsystems for the API."""

    audit_trail: AuditTrail
    policy_engine: PolicyEngine
    design_log: DesignChangeLog
    tracing: TracingManager
    evaluator: OutputEvaluator
    sessions: dict[str, AgentSession] = {}
    _initialized: bool = False

    @classmethod
    async def initialize(cls) -> None:
        if cls._initialized:
            return
        cls.audit_trail = AuditTrail()
        await cls.audit_trail.initialize()

        cls.policy_engine = PolicyEngine()
        rules = PolicyLoader.load_directory(settings.policy_dir)
        cls.policy_engine.load_rules(rules)

        cls.design_log = DesignChangeLog()
        cls.tracing = TracingManager()
        cls.evaluator = OutputEvaluator()
        cls.sessions = {}
        cls._initialized = True

    @classmethod
    def register_session(cls, session: AgentSession) -> None:
        cls.sessions[session.session_id] = session

    @classmethod
    def get_session(cls, session_id: str) -> AgentSession | None:
        return cls.sessions.get(session_id)

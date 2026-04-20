"""AgentSession — the top-level entry point that bootstraps a governed agent run."""

from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

import structlog

from agent_harness.audit import AuditEntry, AuditEventType, AuditTrail
from agent_harness.authorization import AuthorizationContext, LimitTracker, OperationLimits
from agent_harness.config import settings
from agent_harness.control import KillSwitch
from agent_harness.control.override import HumanOverride
from agent_harness.identity import AgentCredential, CredentialManager, DelegationChain, HumanPrincipal
from agent_harness.observability import OutputEvaluator, TracingManager
from agent_harness.orchestration.graph import build_harness_graph
from agent_harness.orchestration.state import HarnessState
from agent_harness.planning.plan import ExecutionPlan
from agent_harness.policy import PolicyEngine, PolicyLoader

logger = structlog.get_logger(__name__)


class AgentSession:
    """Bootstraps a fully governed agent session.

    Usage:
        session = AgentSession(principal=..., scopes=[...])
        await session.initialize()
        result = await session.run(plan)
    """

    def __init__(
        self,
        principal: HumanPrincipal,
        scopes: list[str],
        limits: OperationLimits | None = None,
        credential_ttl: timedelta = timedelta(minutes=15),
        policy_dir: Path | None = None,
    ) -> None:
        self.session_id = str(uuid.uuid4())
        self.agent_id = str(uuid.uuid4())

        self.principal = principal
        self.scopes = scopes
        self.limits = limits or OperationLimits()

        self._cred_mgr = CredentialManager(ttl=credential_ttl)
        self._policy_engine = PolicyEngine()
        self._audit = AuditTrail()
        self._kill_switch = KillSwitch()
        self._override = HumanOverride()
        self._tracing = TracingManager()
        self._evaluator = OutputEvaluator()
        self._policy_dir = policy_dir or settings.policy_dir

        self.credential: AgentCredential | None = None
        self.delegation_chain = DelegationChain()

    async def initialize(self) -> None:
        """Set up all subsystems and issue the initial agent credential."""
        await self._audit.initialize()

        rules = PolicyLoader.load_directory(self._policy_dir)
        self._policy_engine.load_rules(rules)

        self.credential = self._cred_mgr.issue(
            self.agent_id, self.principal.principal_id, self.scopes
        )
        self.delegation_chain.append(
            delegator_id=self.principal.principal_id,
            delegate_id=self.agent_id,
            scopes=self.scopes,
            reason="Session initialization",
        )

        await self._audit.append(
            AuditEntry(
                event_type=AuditEventType.AGENT_CREATED,
                agent_id=self.agent_id,
                principal_id=self.principal.principal_id,
                session_id=self.session_id,
                detail=f"Scopes: {self.scopes}",
            )
        )
        await self._audit.append(
            AuditEntry(
                event_type=AuditEventType.CREDENTIAL_ISSUED,
                agent_id=self.agent_id,
                principal_id=self.principal.principal_id,
                session_id=self.session_id,
                detail=f"TTL: {self.credential.expires_at.isoformat()}",
            )
        )

        logger.info(
            "session.initialized",
            session_id=self.session_id,
            agent_id=self.agent_id,
            scopes=self.scopes,
        )

    async def run(self, plan: ExecutionPlan) -> HarnessState:
        """Execute a plan through the governed LangGraph pipeline."""
        graph = build_harness_graph(
            policy_engine=self._policy_engine,
            audit_trail=self._audit,
            kill_switch=self._kill_switch,
            human_override=self._override,
            tracing=self._tracing,
            evaluator=self._evaluator,
        )
        compiled = graph.compile()

        auth_ctx = AuthorizationContext(granted_scopes=set(self.scopes))
        tracker = LimitTracker(limits=self.limits)

        initial_state = HarnessState(
            principal=self.principal,
            credential=self.credential,
            delegation_chain=self.delegation_chain,
            auth_context=auth_ctx,
            limits=self.limits,
            limit_tracker=tracker,
            plan=plan,
            agent_id=self.agent_id,
            session_id=self.session_id,
        )

        next_step = plan.next_step()
        if next_step:
            initial_state.current_action = next_step.action
            initial_state.current_resource = next_step.resource

        result = await compiled.ainvoke(initial_state)
        return result

    def kill(self, reason: str = "Manual operator kill") -> None:
        from agent_harness.control import KillReason
        self._kill_switch.trigger(
            reason=KillReason.OPERATOR_MANUAL,
            triggered_by=self.principal.principal_id,
            agent_id=self.agent_id,
            session_id=self.session_id,
            detail=reason,
        )

    @property
    def override(self) -> HumanOverride:
        return self._override

    async def verify_audit(self) -> tuple[bool, int]:
        return await self._audit.verify_chain(session_id=self.session_id)

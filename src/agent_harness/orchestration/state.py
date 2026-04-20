"""LangGraph state — the typed state flowing through every node in the graph."""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

from agent_harness.identity import AgentCredential, DelegationChain, HumanPrincipal
from agent_harness.authorization import AuthorizationContext, LimitTracker, OperationLimits
from agent_harness.planning.plan import ExecutionPlan
from agent_harness.policy.engine import PolicyDecision


class HarnessState(BaseModel):
    """Typed state that flows through the LangGraph orchestration.

    Every governance artefact is carried in state so nodes can enforce
    policy, check limits, and record audit entries without side-channel lookups.
    """

    # Message history (LangGraph reducer merges new messages)
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Identity
    principal: HumanPrincipal | None = None
    credential: AgentCredential | None = None
    delegation_chain: DelegationChain | None = None

    # Authorization
    auth_context: AuthorizationContext = Field(default_factory=AuthorizationContext)
    limits: OperationLimits = Field(default_factory=OperationLimits)
    limit_tracker: LimitTracker | None = None

    # Plan
    plan: ExecutionPlan | None = None

    # Runtime
    agent_id: str = ""
    session_id: str = ""
    current_action: str = ""
    current_resource: str = ""
    last_policy_decision: PolicyDecision | None = None
    pending_human_approval: bool = False
    is_killed: bool = False
    error: str | None = None

    # Outputs
    final_output: str | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

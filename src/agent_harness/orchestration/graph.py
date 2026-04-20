"""LangGraph graph definition — the governed agent execution loop.

The graph enforces this sequence for every action:
  1. kill_check    → is the agent halted?
  2. policy_gate   → does policy allow this action?
  3. intent_check  → does this action match the approved plan?
  4. authorize     → does the agent have the required scope + limits?
  5. execute       → run the tool / LLM call
  6. evaluate      → verify the output (DeepEval)
  7. audit         → append to the tamper-evident log
  8. route         → next step or finish
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

import structlog
from langgraph.graph import END, StateGraph

from agent_harness.audit import AuditEntry, AuditEventType, AuditTrail
from agent_harness.authorization.limits import ResourceExhaustedError
from agent_harness.control import KillReason, KillSwitch
from agent_harness.control.kill_switch import AgentKilledError
from agent_harness.control.override import HumanOverride
from agent_harness.observability import OutputEvaluator, TracingManager
from agent_harness.orchestration.state import HarnessState
from agent_harness.planning.intent import IntentBinder
from agent_harness.policy import PolicyEngine
from agent_harness.policy.engine import PolicyDeniedError, PolicyVerdict

logger = structlog.get_logger(__name__)


def build_harness_graph(
    policy_engine: PolicyEngine,
    audit_trail: AuditTrail,
    kill_switch: KillSwitch,
    human_override: HumanOverride,
    tracing: TracingManager,
    evaluator: OutputEvaluator,
) -> StateGraph:
    """Construct the governed LangGraph state machine."""

    graph = StateGraph(HarnessState)

    # ── Node: kill check ────────────────────────────────────────────────
    async def kill_check(state: HarnessState) -> dict[str, Any]:
        if kill_switch.is_killed:
            return {"is_killed": True, "error": "Agent halted by kill switch."}
        return {"is_killed": False}

    # ── Node: policy gate ───────────────────────────────────────────────
    async def policy_gate(state: HarnessState) -> dict[str, Any]:
        try:
            decision = policy_engine.evaluate_or_raise(
                agent_id=state.agent_id,
                action=state.current_action,
                resource=state.current_resource,
            )
            return {"last_policy_decision": decision, "pending_human_approval": False}
        except PolicyDeniedError as exc:
            await audit_trail.append(
                AuditEntry(
                    event_type=AuditEventType.POLICY_DENIED,
                    agent_id=state.agent_id,
                    session_id=state.session_id,
                    action=state.current_action,
                    resource=state.current_resource,
                    detail=str(exc),
                    policy_decision_id=exc.decision.decision_id,
                )
            )
            return {
                "last_policy_decision": exc.decision,
                "error": str(exc),
                "is_killed": True,
            }

    # ── Node: intent check ──────────────────────────────────────────────
    async def intent_check(state: HarnessState) -> dict[str, Any]:
        if not state.plan:
            return {}
        binder = IntentBinder(state.plan)
        deviation = binder.check_action(state.current_action, state.current_resource)
        if deviation:
            await audit_trail.append(
                AuditEntry(
                    event_type=AuditEventType.DEVIATION_DETECTED,
                    agent_id=state.agent_id,
                    session_id=state.session_id,
                    action=state.current_action,
                    detail=deviation.message,
                    plan_id=state.plan.plan_id,
                )
            )
            return {"pending_human_approval": True, "error": deviation.message}
        return {"pending_human_approval": False}

    # ── Node: authorize ─────────────────────────────────────────────────
    async def authorize(state: HarnessState) -> dict[str, Any]:
        try:
            state.auth_context.check_or_raise(
                state.current_action, f"execute {state.current_action}"
            )
            if state.limit_tracker:
                state.limit_tracker.record_tool_call()
        except (PermissionError, ResourceExhaustedError) as exc:
            await audit_trail.append(
                AuditEntry(
                    event_type=AuditEventType.LIMIT_EXCEEDED
                    if isinstance(exc, ResourceExhaustedError)
                    else AuditEventType.POLICY_DENIED,
                    agent_id=state.agent_id,
                    session_id=state.session_id,
                    action=state.current_action,
                    detail=str(exc),
                )
            )
            return {"error": str(exc), "is_killed": True}
        return {}

    # ── Node: execute (placeholder — wired to actual tools at runtime) ──
    async def execute(state: HarnessState) -> dict[str, Any]:
        input_hash = hashlib.sha256(state.current_action.encode()).hexdigest()
        await audit_trail.append(
            AuditEntry(
                event_type=AuditEventType.ACTION_STARTED,
                agent_id=state.agent_id,
                session_id=state.session_id,
                action=state.current_action,
                resource=state.current_resource,
                input_hash=input_hash,
            )
        )
        # Actual tool execution is injected via the session runtime.
        # This node is a governance boundary — real work happens in subgraphs.
        return {"final_output": "[execution placeholder]"}

    # ── Node: evaluate output ───────────────────────────────────────────
    async def evaluate(state: HarnessState) -> dict[str, Any]:
        if not state.final_output:
            return {}
        results = evaluator.evaluate(
            input_text=state.current_action,
            output_text=state.final_output,
        )
        failures = [r for r in results if r.status.value == "fail"]
        if failures:
            names = ", ".join(f.metric_name for f in failures)
            await audit_trail.append(
                AuditEntry(
                    event_type=AuditEventType.ACTION_FAILED,
                    agent_id=state.agent_id,
                    session_id=state.session_id,
                    action=state.current_action,
                    detail=f"DeepEval failures: {names}",
                )
            )
            return {"error": f"Output evaluation failed: {names}"}
        return {}

    # ── Node: audit ─────────────────────────────────────────────────────
    async def audit(state: HarnessState) -> dict[str, Any]:
        output_hash = ""
        if state.final_output:
            output_hash = hashlib.sha256(state.final_output.encode()).hexdigest()
        await audit_trail.append(
            AuditEntry(
                event_type=AuditEventType.ACTION_COMPLETED,
                agent_id=state.agent_id,
                session_id=state.session_id,
                action=state.current_action,
                resource=state.current_resource,
                output_hash=output_hash,
            )
        )
        return {}

    # ── Routing ─────────────────────────────────────────────────────────
    def should_continue(state: HarnessState) -> Literal["end", "policy_gate"]:
        if state.is_killed or state.error:
            return "end"
        if state.plan:
            next_step = state.plan.next_step()
            if next_step:
                return "policy_gate"
        return "end"

    def after_kill_check(state: HarnessState) -> Literal["end", "policy_gate"]:
        if state.is_killed:
            return "end"
        return "policy_gate"

    def after_policy(state: HarnessState) -> Literal["end", "intent_check"]:
        if state.is_killed or state.error:
            return "end"
        return "intent_check"

    def after_intent(state: HarnessState) -> Literal["end", "authorize"]:
        if state.pending_human_approval or state.error:
            return "end"
        return "authorize"

    def after_auth(state: HarnessState) -> Literal["end", "execute"]:
        if state.is_killed or state.error:
            return "end"
        return "execute"

    def after_execute(state: HarnessState) -> str:
        return "evaluate"

    def after_evaluate(state: HarnessState) -> Literal["end", "audit"]:
        if state.error:
            return "end"
        return "audit"

    # ── Wire the graph ──────────────────────────────────────────────────
    graph.add_node("kill_check", kill_check)
    graph.add_node("policy_gate", policy_gate)
    graph.add_node("intent_check", intent_check)
    graph.add_node("authorize", authorize)
    graph.add_node("execute", execute)
    graph.add_node("evaluate", evaluate)
    graph.add_node("audit", audit)

    graph.set_entry_point("kill_check")
    graph.add_conditional_edges("kill_check", after_kill_check, {"end": END, "policy_gate": "policy_gate"})
    graph.add_conditional_edges("policy_gate", after_policy, {"end": END, "intent_check": "intent_check"})
    graph.add_conditional_edges("intent_check", after_intent, {"end": END, "authorize": "authorize"})
    graph.add_conditional_edges("authorize", after_auth, {"end": END, "execute": "execute"})
    graph.add_edge("execute", "evaluate")
    graph.add_conditional_edges("evaluate", after_evaluate, {"end": END, "audit": "audit"})
    graph.add_conditional_edges("audit", should_continue, {"end": END, "policy_gate": "policy_gate"})

    return graph

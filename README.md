# Agent Harness

Secure, governed agent orchestration for enterprise software.

Agent Harness provides a hardened execution layer for LLM-powered agents, enforcing identity, authorization, policy, and auditability at every action boundary. It is designed for environments where agents operate on behalf of humans and must be traceable, controllable, and compliant.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Session                            │
│  ┌───────────┐  ┌───────────────┐  ┌────────────────────────┐  │
│  │ Principal  │──│  Delegation   │──│   Credential Manager   │  │
│  │ (Human)    │  │  Chain        │  │   (ECDSA, short-lived) │  │
│  └───────────┘  └───────────────┘  └────────────────────────┘  │
│                                                                 │
│  ┌──────────────────── LangGraph Loop ────────────────────────┐ │
│  │                                                            │ │
│  │  kill_check → policy_gate → intent_check → authorize       │ │
│  │       │            │              │             │           │ │
│  │       │            │              │             ▼           │ │
│  │       │            │              │          execute        │ │
│  │       │            │              │             │           │ │
│  │       │            │              │             ▼           │ │
│  │       │            │              │          evaluate       │ │
│  │       │            │              │             │           │ │
│  │       │            │              │             ▼           │ │
│  │       ▼            ▼              ▼           audit         │ │
│  │     [HALT]      [DENY]       [ESCALATE]        │           │ │
│  │                                           next step / END  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ LangFuse     │  │ DeepEval     │  │ Tamper-Evident Audit  │ │
│  │ Tracing      │  │ Verification │  │ (hash-chained log)    │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| **Per-agent identity** | Each agent instance gets a UUID, cryptographic binding to the human principal via ECDSA-signed JWT, and a traceable delegation chain with scope intersection |
| **Scoped authorization** | Explicit tool/data/action scopes; dollar/operation/time limits enforced at every action boundary |
| **Policy-as-code** | YAML policy definitions evaluated by a deterministic engine (deny-wins model); denials are logged and terminal |
| **Plan validation** | Actions bound to a hash-sealed execution plan; deviations trigger human approval |
| **Tamper-evident audit** | Hash-chained, append-only log of all prompts, tool calls, policy decisions, and outcomes; stored in SQL with chain verification |
| **Kill switch & override** | Cooperative kill checked at every action boundary; async human-in-the-loop approval for escalations |

## Tech Stack

- **LangGraph** — Orchestration state machine with typed state
- **LangChain** — LLM and tool integration
- **LangFuse** — Distributed tracing and observability
- **DeepEval** — Output quality/safety verification (faithfulness, relevancy, toxicity, bias)
- **Microsoft Agent Governance Toolkit** — Policy-as-code format compatibility
- **SQLAlchemy + aiosqlite** — Persistent audit trail
- **cryptography + PyJWT** — ECDSA credential signing
- **structlog** — Structured JSON logging
- **Pydantic** — Typed configuration and data models

## Project Structure

```
src/agent_harness/
├── config.py                  # Centralized settings from env
├── identity/                  # Principal, credentials, delegation
│   ├── principal.py           # Human principal binding (SHA-256 fingerprint)
│   ├── credentials.py         # Short-lived ECDSA JWTs
│   └── delegation.py          # Hash-verified delegation chains
├── authorization/             # Scoped permissions and limits
│   ├── scopes.py              # Tool/data/action scope registry
│   └── limits.py              # Dollar, call count, wall clock limits
├── policy/                    # Deterministic policy engine
│   ├── engine.py              # Evaluate actions, deny-wins model
│   └── loader.py              # Load YAML policy definitions
├── planning/                  # Plan validation and intent binding
│   ├── plan.py                # Hash-sealed execution plans
│   ├── validator.py           # Pre-approval plan validation
│   └── intent.py              # Runtime deviation detection
├── audit/                     # Tamper-evident audit trail
│   ├── models.py              # AuditEntry + SQLAlchemy table
│   └── trail.py               # Hash-chained append + verification
├── observability/             # Tracing and evaluation
│   ├── tracing.py             # LangFuse integration
│   └── evaluation.py          # DeepEval output verification
├── control/                   # Runtime control plane
│   ├── kill_switch.py         # Cooperative halt mechanism
│   └── override.py            # Human-in-the-loop approval
├── orchestration/             # LangGraph wiring
│   ├── state.py               # Typed graph state
│   ├── graph.py               # Governed execution graph
│   └── session.py             # Session bootstrap
└── logging/                   # Structured logging
    ├── design_log.py          # Configuration change tracking
    └── runtime_log.py         # Runtime activity capture
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/mikecurr55/agent-harness.git
cd agent-harness
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest
```

## Usage

```python
import asyncio
from agent_harness.identity import HumanPrincipal
from agent_harness.authorization import OperationLimits
from agent_harness.planning.plan import ExecutionPlan, PlanStep
from agent_harness.orchestration import AgentSession

async def main():
    principal = HumanPrincipal(external_subject="user@company.com")

    session = AgentSession(
        principal=principal,
        scopes=["tool:read:*", "llm:invoke", "data:customer"],
        limits=OperationLimits(max_tool_calls=20, max_dollar_spend="5.00"),
    )
    await session.initialize()

    plan = ExecutionPlan(
        agent_id=session.agent_id,
        principal_id=principal.principal_id,
        steps=[
            PlanStep(order=1, action="tool:read:search", resource="data:customer",
                     description="Search customer records"),
            PlanStep(order=2, action="llm:invoke", resource="*",
                     description="Summarize results"),
        ],
    )
    plan.approve(principal.principal_id)

    result = await session.run(plan)

    valid, count = await session.verify_audit()
    print(f"Audit chain valid: {valid}, entries: {count}")

asyncio.run(main())
```

## Policy Definitions

Policies are YAML files in the `policies/` directory:

```yaml
policies:
  - id: allow-read-tools
    description: "Allow agents to invoke read-only tools"
    action: "tool:read:*"
    resource: "*"
    verdict: allow
    priority: 10

  - id: deny-pii-access
    description: "Block PII access without explicit scope"
    action: "*"
    resource: "data:pii:*"
    verdict: deny
    priority: 100
```

## License

MIT

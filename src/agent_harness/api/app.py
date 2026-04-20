"""FastAPI application — the HTTP boundary for the Agent Harness UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_harness.api.state import AppState
from agent_harness.api.routes import sessions, audit, overrides, policies, dashboard
from agent_harness.logging.runtime_log import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(json_output=False)
    await AppState.initialize()
    yield


app = FastAPI(
    title="Agent Harness",
    version="0.1.0",
    description="Secure, governed agent orchestration for the enterprise",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(overrides.router, prefix="/api/overrides", tags=["overrides"])
app.include_router(policies.router, prefix="/api/policies", tags=["policies"])

"""LangFuse integration — traces every LLM call, tool invocation, and agent step."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import structlog
from langfuse import Langfuse

from agent_harness.config import settings

logger = structlog.get_logger(__name__)


class TracingManager:
    """Wraps the LangFuse client to provide structured trace/span lifecycle.

    Traces are tagged with agent_id and session_id for correlation with the
    audit trail.  Falls back to no-op logging if LangFuse is not configured.
    """

    def __init__(self) -> None:
        self._client: Langfuse | None = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            logger.info("tracing.langfuse_connected", host=settings.langfuse_host)
        else:
            logger.warning("tracing.langfuse_not_configured")

    def create_trace(
        self,
        name: str,
        agent_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if not self._client:
            logger.debug("tracing.noop_trace", name=name)
            return None
        trace = self._client.trace(
            name=name,
            session_id=session_id,
            metadata={"agent_id": agent_id, **(metadata or {})},
        )
        return trace

    @contextmanager
    def span(
        self,
        trace: Any,
        name: str,
        input_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager that opens a LangFuse span and closes it with output."""
        context: dict[str, Any] = {"output": None, "error": None}
        span_obj = None
        if trace and self._client:
            span_obj = trace.span(
                name=name,
                input=input_data,
                metadata=metadata or {},
            )
        try:
            yield context
        except Exception as exc:
            context["error"] = str(exc)
            raise
        finally:
            if span_obj:
                span_obj.end(output=context.get("output"), metadata={"error": context.get("error")})

    def log_generation(
        self,
        trace: Any,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        usage: dict[str, int] | None = None,
    ) -> None:
        if trace and self._client:
            trace.generation(
                name=name,
                model=model,
                input=prompt,
                output=completion,
                usage=usage or {},
            )

    def flush(self) -> None:
        if self._client:
            self._client.flush()

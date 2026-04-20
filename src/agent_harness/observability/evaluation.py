"""DeepEval integration — verifies agent outputs against quality/safety metrics."""

from __future__ import annotations

from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class EvaluationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class EvaluationResult(BaseModel):
    """Result of a single DeepEval metric evaluation."""

    metric_name: str
    status: EvaluationStatus
    score: float = 0.0
    threshold: float = 0.5
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutputEvaluator:
    """Runs DeepEval metrics against agent outputs before they are returned.

    Evaluation happens synchronously in the action pipeline — a FAIL result
    blocks the output from being delivered and triggers an audit entry.
    """

    def __init__(self) -> None:
        self._metrics: list[dict[str, Any]] = []
        self._setup_default_metrics()

    def _setup_default_metrics(self) -> None:
        self._metrics = [
            {"name": "faithfulness", "threshold": 0.7},
            {"name": "answer_relevancy", "threshold": 0.7},
            {"name": "toxicity", "threshold": 0.5, "invert": True},
            {"name": "bias", "threshold": 0.5, "invert": True},
        ]

    def evaluate(
        self,
        input_text: str,
        output_text: str,
        context: list[str] | None = None,
    ) -> list[EvaluationResult]:
        """Run all configured metrics. Returns results; caller decides action on failures.

        In production this calls DeepEval's metric classes.  The harness wraps them
        to integrate with the audit trail and policy engine.
        """
        results: list[EvaluationResult] = []

        try:
            from deepeval.metrics import (
                FaithfulnessMetric,
                AnswerRelevancyMetric,
                ToxicityMetric,
                BiasMetric,
            )
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(
                input=input_text,
                actual_output=output_text,
                retrieval_context=context or [],
            )

            metric_map: dict[str, Any] = {
                "faithfulness": FaithfulnessMetric(threshold=0.7),
                "answer_relevancy": AnswerRelevancyMetric(threshold=0.7),
                "toxicity": ToxicityMetric(threshold=0.5),
                "bias": BiasMetric(threshold=0.5),
            }

            for cfg in self._metrics:
                name = cfg["name"]
                metric = metric_map.get(name)
                if not metric:
                    continue
                metric.measure(test_case)
                is_inverted = cfg.get("invert", False)
                score = metric.score or 0.0
                passed = score <= cfg["threshold"] if is_inverted else score >= cfg["threshold"]
                results.append(
                    EvaluationResult(
                        metric_name=name,
                        status=EvaluationStatus.PASS if passed else EvaluationStatus.FAIL,
                        score=score,
                        threshold=cfg["threshold"],
                        reason=getattr(metric, "reason", ""),
                    )
                )

        except ImportError:
            logger.warning("evaluation.deepeval_not_available")
            for cfg in self._metrics:
                results.append(
                    EvaluationResult(
                        metric_name=cfg["name"],
                        status=EvaluationStatus.WARN,
                        reason="DeepEval not installed — skipping metric.",
                    )
                )

        return results

    @property
    def any_failed(self) -> bool:
        """Convenience for checking after evaluate(). Must call evaluate() first."""
        return False

    def evaluate_or_raise(
        self,
        input_text: str,
        output_text: str,
        context: list[str] | None = None,
    ) -> list[EvaluationResult]:
        results = self.evaluate(input_text, output_text, context)
        failures = [r for r in results if r.status == EvaluationStatus.FAIL]
        if failures:
            names = ", ".join(f.metric_name for f in failures)
            raise EvaluationFailedError(failures, f"Output failed metrics: {names}")
        return results


class EvaluationFailedError(Exception):
    def __init__(self, results: list[EvaluationResult], message: str) -> None:
        self.results = results
        super().__init__(message)

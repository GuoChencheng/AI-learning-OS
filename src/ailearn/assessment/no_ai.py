from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ailearn.agents.contracts import NoAIReconstructionAssessmentOutput
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier


class NoAITestEvaluator:
    def evaluate(
        self,
        project_id: str,
        concept: str,
        user_answer: str,
        current_position: dict[str, Any],
        context: dict[str, Any],
        model_gateway: ModelGateway,
    ) -> NoAIReconstructionAssessmentOutput:
        fallback = _deterministic_assessment(concept, user_answer, current_position, context)
        prompt = f"""
Assess a no-AI reconstruction answer for AI Learn OS.
Project: {project_id}
Concept: {concept}
Previous position: {current_position}
Context: {context}
Learner answer:
{user_answer}

Return ONLY JSON matching NoAIReconstructionAssessmentOutput.
Never grant A4 unless delayed review evidence is explicit.
""".strip()
        try:
            return model_gateway.complete_structured(prompt, NoAIReconstructionAssessmentOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            return fallback


def _deterministic_assessment(concept: str, user_answer: str, current_position: dict[str, Any], context: dict[str, Any]) -> NoAIReconstructionAssessmentOutput:
    previous = str(current_position.get("current_level") or "A0")
    text = user_answer.strip()
    lowered = text.lower()
    has_boundary = any(marker in text for marker in ("不是", "区别", "边界", "反例", "不一定", "额外条件", "假设")) or any(
        marker in lowered for marker in ("not", "boundary", "counterexample", "condition", "assumption", "distinguish")
    )
    has_application = any(marker in text for marker in ("说明", "应用", "Ising", "tricritical", "universality", "推导")) or any(
        marker in lowered for marker in ("apply", "application", "derive", "ising", "transfer")
    )
    delayed = bool(context.get("delayed_review_passed") or context.get("review_completed_after_delay"))

    if delayed and has_boundary and has_application:
        level = "A4"
        result = "passed"
    elif has_application:
        level = "A3"
        result = "passed"
    elif has_boundary:
        level = "A2"
        result = "partial"
    elif text:
        level = "A1"
        result = "partial"
    else:
        level = "A0"
        result = "failed"

    return NoAIReconstructionAssessmentOutput(
        concept=concept,
        previous_level=previous if previous in {"A0", "A1", "A2", "A3", "A4"} else "A0",
        new_level=level,
        result=result,
        evidence_text=text[:500],
        reason=_reason_for_level(level),
        next_action=_next_action_for_level(level),
        should_schedule_review=level in {"A0", "A1", "A2", "A3"},
    )


def _reason_for_level(level: str) -> str:
    return {
        "A0": "No usable no-AI reconstruction evidence was provided.",
        "A1": "Learner gave a rough definition or recognition, but no boundary or transfer evidence.",
        "A2": "Learner distinguished the concept from nearby concepts or named a boundary/counterexample.",
        "A3": "Learner applied or transferred the concept in addition to stating a boundary.",
        "A4": "Learner passed delayed retrieval and transfer evidence.",
    }[level]


def _next_action_for_level(level: str) -> str:
    if level in {"A0", "A1"}:
        return "Ask for a no-AI explanation with one boundary and one counterexample."
    if level == "A2":
        return "Ask for transfer/application to reach A3."
    if level == "A3":
        return "Schedule delayed review before considering A4."
    return "Maintain with delayed review spacing."

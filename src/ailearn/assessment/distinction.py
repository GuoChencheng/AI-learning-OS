from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError

from ailearn.agents.contracts import DistinctionAssessmentOutput
from ailearn.db.repository import Repository
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier


class DistinctionTestEvaluator:
    def evaluate(
        self,
        project_id: str,
        distinction_id: str,
        user_answer: str,
        model_gateway: ModelGateway,
        repository: Repository,
    ) -> DistinctionAssessmentOutput:
        distinction = repository.get_by_id("distinctions", distinction_id)
        if not distinction or distinction.get("project_id") != project_id:
            raise KeyError(distinction_id)
        fallback = _deterministic_assessment(distinction, user_answer)
        prompt = f"""
Assess this distinction test for AI Learn OS.
Distinction: {distinction}
Learner answer:
{user_answer}

Return ONLY JSON matching DistinctionAssessmentOutput.
Mark clear only when the learner gives a boundary and preserves non-identity.
""".strip()
        try:
            result = model_gateway.complete_structured(prompt, DistinctionAssessmentOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            result = fallback
        next_time = _next_test_time() if result.should_schedule_retest else None
        repository.update_distinction_assessment(
            distinction_id,
            {**result.model_dump(mode="json"), "next_distinction_test_at": next_time},
        )
        repository.log_assessment_update(
            project_id,
            None,
            "distinction_assessment",
            {
                "distinction_id": distinction_id,
                "result": result.model_dump(mode="json"),
                "source_metadata": {"source_type": "user_answer", "evidence_text": user_answer[:500]},
            },
        )
        if result.should_schedule_retest:
            repository.create_review_trigger(
                project_id,
                {
                    "target": f"{result.concept_a} vs {result.concept_b}",
                    "trigger_reason": result.reason,
                    "review_type": "distinguish",
                    "scheduled_time": next_time or _next_test_time(),
                    "success_criteria": result.next_test_question or "State boundary, counterexample, and example without AI help.",
                },
            )
        return result


def _deterministic_assessment(distinction: dict[str, Any], answer: str) -> DistinctionAssessmentOutput:
    text = " ".join(answer.strip().split())
    lowered = text.lower()
    wrong_equivalence = _wrong_equivalence(text, lowered)
    has_boundary = _has_boundary(text, lowered)
    has_example_or_counterexample = _has_example_or_counterexample(text, lowered)

    if wrong_equivalence:
        status = "failed"
        delta = 1
        reason = "The answer collapses the two concepts again."
        next_question = "State one condition under which these two concepts should not be identified."
        schedule = True
    elif has_boundary and has_example_or_counterexample:
        status = "clear"
        delta = 0
        reason = "The answer gives a boundary and an example/counterexample."
        next_question = None
        schedule = False
    elif has_boundary:
        status = "partially_clear"
        delta = 0
        reason = "The answer keeps the concepts apart but lacks a decisive example or counterexample."
        next_question = "Give one example and one counterexample for this boundary."
        schedule = True
    else:
        status = "partially_clear" if text else "needs_test"
        delta = 0
        reason = "The answer is too vague to confirm the distinction."
        next_question = "Give a boundary, an example, and a counterexample."
        schedule = True

    return DistinctionAssessmentOutput(
        concept_a=str(distinction.get("concept_a", "")),
        concept_b=str(distinction.get("concept_b", "")),
        status=status,
        confusion_count_delta=delta,
        evidence_text=text[:500],
        reason=reason,
        next_test_question=next_question,
        should_schedule_retest=schedule,
    )


def _wrong_equivalence(text: str, lowered: str) -> bool:
    if any(marker in text for marker in ("不完全一样", "不是完全一样", "不等同", "不是")) or any(marker in lowered for marker in ("not identical", "not the same", "not exactly")):
        return False
    return any(marker in text for marker in ("就是", "完全一样", "等同", "相同")) or any(marker in lowered for marker in ("exactly", "identical", "same as", "equals"))


def _has_boundary(text: str, lowered: str) -> bool:
    return any(marker in text for marker in ("不是", "不完全", "边界", "区别", "额外结构", "条件", "OPE", "拓扑", "类比")) or any(
        marker in lowered for marker in ("not", "boundary", "condition", "ope", "topological", "analogy", "different")
    )


def _has_example_or_counterexample(text: str, lowered: str) -> bool:
    return any(marker in text for marker in ("例如", "反例", "可以类比", "任意子", "拓扑相", "表示范畴")) or any(
        marker in lowered for marker in ("example", "counterexample", "anyon", "modular", "category")
    )


def _next_test_time() -> str:
    return (datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)).isoformat().replace("+00:00", "Z")

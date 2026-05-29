from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from ailearn.agents.contracts import DerivationStepAssessmentOutput
from ailearn.db.repository import Repository
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier


class DerivationTrustEvaluator:
    def evaluate_step(
        self,
        project_id: str,
        record_id: str,
        user_attempt: str,
        model_gateway: ModelGateway,
        repository: Repository,
    ) -> DerivationStepAssessmentOutput:
        record = repository.get_by_id("derivation_trust_records", record_id)
        if not record or record.get("project_id") != project_id:
            raise KeyError(record_id)
        fallback = _deterministic_assessment(record, user_attempt)
        prompt = f"""
Assess this learner derivation attempt for AI Learn OS.
Record: {record}
Learner attempt:
{user_attempt}

Return ONLY JSON matching DerivationStepAssessmentOutput.
Do not mark AI-hinted steps as user-derived.
""".strip()
        try:
            result = model_gateway.complete_structured(prompt, DerivationStepAssessmentOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            result = fallback
        repository.update_derivation_trust_assessment(
            record_id,
            {**result.model_dump(mode="json"), "next_rederive_time": _next_rederive_time() if result.should_schedule_rederive else None},
        )
        repository.log_assessment_update(
            project_id,
            None,
            "derivation_assessment",
            {"record_id": record_id, "result": result.model_dump(mode="json"), "source_metadata": {"source_type": "user_answer", "evidence_text": user_attempt}},
        )
        return result


def _deterministic_assessment(record: dict, user_attempt: str) -> DerivationStepAssessmentOutput:
    done: list[str] = []
    untrusted: list[str] = []
    text = user_attempt.lower()
    for step in record.get("key_steps", []):
        if str(step).lower() in text or _soft_step_match(str(step), user_attempt):
            done.append(str(step))
    for assumption in record.get("assumptions", []):
        if str(assumption) and str(assumption) not in user_attempt:
            untrusted.append(f"Missing assumption: {assumption}")
    if not done:
        untrusted.append("No key derivation step was independently reconstructed.")
    status = "passed" if done and not untrusted else "partial" if done else "failed"
    return DerivationStepAssessmentOutput(
        result_or_tool=str(record.get("result_or_tool", "")),
        done_by_user=done,
        hinted_by_ai=list(record.get("hinted_by_ai", [])),
        untrusted_steps=untrusted,
        no_ai_reconstruction_status=status,
        reason="Learner-derived steps and missing assumptions were separated.",
        next_action="Re-derive the untrusted steps without hints." if untrusted else "Mark this derivation as trusted and schedule delayed reconstruction.",
        should_schedule_rederive=bool(untrusted),
    )


def _soft_step_match(step: str, attempt: str) -> bool:
    tokens = [token for token in step.replace("，", " ").replace(",", " ").split() if len(token) >= 2]
    return bool(tokens) and all(token in attempt for token in tokens[:2])


def _next_rederive_time() -> str:
    return (datetime.now(UTC).replace(microsecond=0) + timedelta(days=3)).isoformat().replace("+00:00", "Z")


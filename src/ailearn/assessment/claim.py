from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ailearn.agents.contracts import ClaimEpistemicAssessmentOutput
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier


class ClaimEpistemicEvaluator:
    def evaluate(
        self,
        project_id: str,
        claim: dict[str, Any] | None,
        user_statement: str,
        context_pack: dict[str, Any] | None,
        model_gateway: ModelGateway,
    ) -> ClaimEpistemicAssessmentOutput:
        fallback = _deterministic_assessment(claim, user_statement)
        prompt = f"""
Assess this learner-originated claim for AI Learn OS.
Project: {project_id}
Existing claim: {claim or {}}
Context pack: {context_pack or {}}
Learner statement:
{user_statement}

Return ONLY JSON matching ClaimEpistemicAssessmentOutput.
Do not mark strict_fact without reference/context support.
Keep analogy, inference, heuristic, learning_strategy, wrong, and open_question distinct.
""".strip()
        try:
            return model_gateway.complete_structured(prompt, ClaimEpistemicAssessmentOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            return fallback


def _deterministic_assessment(claim: dict[str, Any] | None, statement: str) -> ClaimEpistemicAssessmentOutput:
    text = " ".join(statement.strip().split())
    lowered = text.lower()
    claim_id = str(claim.get("id")) if claim and claim.get("id") else None

    if _is_learning_strategy(text, lowered):
        return ClaimEpistemicAssessmentOutput(
            claim_id=claim_id,
            original_statement=text,
            epistemic_status="learning_strategy",
            status="active",
            confidence=0.78,
            strict_part=None,
            caveat="This is a strategy for sequencing learning, not a disciplinary fact.",
            correction=None,
            evidence_text=text[:500],
            reason="The statement is about how to learn or which example to start from.",
        )
    if _is_open_question(text, lowered):
        return ClaimEpistemicAssessmentOutput(
            claim_id=claim_id,
            original_statement=text,
            epistemic_status="open_question",
            status="open_question",
            confidence=0.7,
            strict_part=None,
            caveat="Needs learner-side verification before becoming a claim.",
            correction=None,
            evidence_text=text[:500],
            reason="The user posed a question rather than asserting a settled claim.",
        )
    if _is_exact_equivalence_error(text, lowered):
        correction = _correction_for_error(text, lowered)
        return ClaimEpistemicAssessmentOutput(
            claim_id=claim_id,
            original_statement=text,
            epistemic_status="wrong",
            status="wrong",
            confidence=0.86,
            strict_part=None,
            caveat="A structural relation or analogy is being collapsed into identity.",
            correction=correction,
            evidence_text=text[:500],
            reason="The wording asserts exact equivalence where AI Learn OS should preserve a boundary.",
        )
    if _is_analogy_or_inference(text, lowered):
        status = "active"
        epistemic = "analogy" if any(marker in lowered for marker in ("resembles", "analog", "similar", "like")) or any(marker in text for marker in ("类似", "像", "类比")) else "inference"
        return ClaimEpistemicAssessmentOutput(
            claim_id=claim_id,
            original_statement=text,
            epistemic_status=epistemic,
            status=status,
            confidence=0.66,
            strict_part=None,
            caveat="Treat this as a relation to test, not as identity.",
            correction=None,
            evidence_text=text[:500],
            reason="The statement preserves non-identity language and should remain caveated.",
        )
    return ClaimEpistemicAssessmentOutput(
        claim_id=claim_id,
        original_statement=text,
        epistemic_status="inference",
        status="active",
        confidence=0.55,
        strict_part=None,
        caveat="Needs source support or no-AI reconstruction evidence before stronger marking.",
        correction=None,
        evidence_text=text[:500],
        reason="Defaulting to inference because the statement is learner-originated and not directly verified.",
    )


def _is_open_question(text: str, lowered: str) -> bool:
    return "?" in text or "？" in text or any(marker in text for marker in ("吗", "是不是", "是否", "为什么", "什么")) or lowered.startswith(("is ", "are ", "why ", "what ", "how "))


def _is_learning_strategy(text: str, lowered: str) -> bool:
    return any(marker in lowered for marker in ("good first example", "first example", "learn", "study plan")) or any(marker in text for marker in ("学习", "入门", "先学", "第一例子", "第一个例子"))


def _is_exact_equivalence_error(text: str, lowered: str) -> bool:
    equivalence = any(marker in lowered for marker in (" exactly ", " equals ", "same as", "identical", " is exactly ")) or any(marker in text for marker in ("就是", "完全一样", "等同", "相同"))
    cft_anyon = "cft" in lowered and "fusion" in lowered and ("anyon" in lowered or "任意子" in text)
    primary_desc = ("primary" in lowered and "descendant" in lowered) or ("主场" in text and "后代" in text)
    ope_fusion = "fusion rule" in lowered and "ope" in lowered and equivalence
    return equivalence and (cft_anyon or primary_desc or ope_fusion or "cft" in lowered)


def _correction_for_error(text: str, lowered: str) -> str:
    if "anyon" in lowered or "任意子" in text:
        return "CFT fusion can be related to anyon fusion in structured examples, but it is not literally identical by default."
    if "primary" in lowered or "主场" in text:
        return "Primary fields and descendants occupy different roles in a conformal family."
    if "ope" in lowered:
        return "Fusion rules summarize allowed families; the full OPE contains coefficients and descendant data."
    return "Replace exact equivalence with a tested boundary or analogy."


def _is_analogy_or_inference(text: str, lowered: str) -> bool:
    return any(marker in lowered for marker in ("resembles", "analog", "similar", "like", "plausible", "suggests")) or any(marker in text for marker in ("类似", "像", "类比", "可能", "推测"))

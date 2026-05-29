from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError

from ailearn.agents.contracts import NewTemporalTrace, StateWriterOutput
from ailearn.db.repository import Repository
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier
from ailearn.state_writer.service import StateWriterService


class LearningUnitCloseDistiller:
    def __init__(self, model_gateway: ModelGateway) -> None:
        self.model_gateway = model_gateway

    def distill_and_close(self, project_id: str, unit_id: str, close_reason: str, repository: Repository) -> dict[str, Any]:
        unit = repository.get_by_id("learning_units", unit_id)
        if not unit:
            raise KeyError(unit_id)
        turns = repository.list_learning_unit_turns(unit_id, limit=50)
        summary = _unit_summary(unit, turns, close_reason)
        fallback = _fallback_state_writer_output(unit, turns, close_reason, summary)
        prompt = _distill_prompt(unit, turns, close_reason, fallback)
        try:
            output = self.model_gateway.complete_structured(prompt, StateWriterOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            output = fallback
        output = _sanitize_unit_distillation(output, fallback, unit, turns)
        repository.update_learning_unit(unit_id, {"unit_summary": summary})
        updates = StateWriterService(repository).apply(project_id, unit.get("last_message_id"), output)
        closed = repository.close_learning_unit(unit_id, close_reason)
        return {"unit": closed, "state_updates": updates}


def _unit_summary(unit: dict[str, Any], turns: list[dict[str, Any]], close_reason: str) -> str:
    user_turns = [turn.get("turn_summary", "") for turn in turns if turn.get("role") == "user"]
    focus = " / ".join(text for text in user_turns[:3] if text)
    if not focus:
        focus = unit.get("topic", "current learning topic")
    return f"{unit.get('method', 'learning')} unit on {unit.get('topic', 'current topic')} closed by {close_reason}. Learner-side evidence: {focus[:360]}"


def _fallback_state_writer_output(unit: dict[str, Any], turns: list[dict[str, Any]], close_reason: str, summary: str) -> StateWriterOutput:
    scheduled = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    user_text = " ".join(turn.get("turn_summary", "") for turn in turns if turn.get("role") == "user")
    topic = unit.get("topic") or "learning unit"
    method = unit.get("method") or "concept_explainer"
    data: dict[str, Any] = {
        "new_claims": [],
        "updated_claims": [],
        "new_distinctions": [],
        "new_temporal_trace": NewTemporalTrace(
            event_type="learning_unit_close",
            user_question=f"close learning unit: {topic}",
            system_response_summary=summary[:240],
            state_change_summary=f"Closed learning unit with reason {close_reason}.",
            next_step="Use Run Next to choose the next learning action.",
        ).model_dump(),
        "knowledge_position_updates": [],
        "derivation_trust_updates": [],
        "review_triggers": [],
        "next_recommended_action": "Use Run Next to choose the next learning action.",
        "source_metadata": {
            "source_type": "system_trace",
            "source_message_id": unit.get("last_message_id"),
            "evidence_text": f"unit_close:{unit.get('id')}:{close_reason}:{user_text[:220]}",
        },
        "user_originated_updates": {"temporal_traces": 1},
        "ai_only_observations": {"unit_close_reason": close_reason, "unit_method": method},
        "discarded_ephemeral_judgments": {"learning_unit_context": "working_memory_only"},
    }
    if _has_boundary_confusion(user_text, method):
        data["new_distinctions"] = [
            {
                "concept_a": topic[:80],
                "concept_b": "nearby concept or hidden assumption",
                "boundary": "The learning unit exposed a learner-side boundary that still needs explicit no-AI testing.",
                "common_confusion": "Treating adjacent concepts or useful descriptions as equivalence.",
                "example": "A critical point can motivate CFT language without making every critical point automatically a CFT.",
                "test_question": "What assumption or counterexample would make the proposed equivalence fail?",
            }
        ]
        data["review_triggers"] = [
            {
                "target": topic,
                "trigger_reason": "Learning unit closed with an unresolved or newly exposed distinction.",
                "review_type": "distinguish",
                "scheduled_time": scheduled,
                "success_criteria": "Learner can state the boundary without AI help.",
            }
        ]
        data["user_originated_updates"] = {"temporal_traces": 1, "distinctions": 1, "review_triggers": 1}
    if method == "derivation_coach" or _mentions_derivation(user_text):
        data["derivation_trust_updates"] = [
            {
                "result_or_tool": topic,
                "assumptions": ["Learning unit involved derivation or derivation trust."],
                "key_steps": ["List assumptions.", "Reconstruct key steps.", "Mark untrusted steps."],
                "done_by_user": [],
                "hinted_by_ai": ["AI supported the unit."],
                "untrusted_steps": ["Independent reconstruction was not fully verified at unit close."],
                "failure_conditions": ["Learner cannot reproduce the derivation without prompts."],
                "no_ai_reconstruction_status": "not_started",
                "next_rederive_time": scheduled,
            }
        ]
        data["user_originated_updates"]["derivation_trust_records"] = 1
    if method == "no_ai_reconstruction_tester" or any(marker in user_text for marker in ("无 AI", "不用 AI", "内化")):
        data["knowledge_position_updates"] = [
            {
                "concept": topic,
                "layer": "no_ai_internalization",
                "reason": "Unit close involved no-AI/internalization evidence.",
                "target_level": "A3",
                "current_level": "A1",
                "review_needed": True,
            }
        ]
        data["user_originated_updates"]["knowledge_positions"] = 1
    return StateWriterOutput.model_validate(data)


def _distill_prompt(unit: dict[str, Any], turns: list[dict[str, Any]], close_reason: str, fallback: StateWriterOutput) -> str:
    return f"""
Distill this short-lived AI Learn OS learning unit into structured learner-state updates.
Return ONLY JSON matching StateWriterOutput.

Fallback shape:
{fallback.model_dump_json()}

Unit:
{unit}

Turns:
{turns}

Close reason:
{close_reason}

Rules:
- Durable records must be grounded in user-side evidence from turns.
- Do not save AI explanations as learner understanding.
- Prefer a temporal trace only for low-content units.
- Add DerivationTrust only for derivation attempts/trust gaps.
- Add KnowledgePosition only for no-AI/internalization evidence.
""".strip()


def _sanitize_unit_distillation(output: StateWriterOutput, fallback: StateWriterOutput, unit: dict[str, Any], turns: list[dict[str, Any]]) -> StateWriterOutput:
    data = output.model_dump(mode="json")
    data["source_metadata"] = fallback.source_metadata.model_dump(mode="json")
    user_text = " ".join(turn.get("turn_summary", "") for turn in turns if turn.get("role") == "user")
    method = unit.get("method") or ""
    if not user_text.strip():
        return fallback
    if method != "derivation_coach" and not _mentions_derivation(user_text):
        data["derivation_trust_updates"] = fallback.model_dump(mode="json")["derivation_trust_updates"]
    if method != "no_ai_reconstruction_tester" and not any(marker in user_text for marker in ("无 AI", "不用 AI", "内化")):
        data["knowledge_position_updates"] = fallback.model_dump(mode="json")["knowledge_position_updates"]
    if not data.get("new_temporal_trace"):
        data["new_temporal_trace"] = fallback.new_temporal_trace.model_dump(mode="json")
    data["discarded_ephemeral_judgments"] = {
        **data.get("discarded_ephemeral_judgments", {}),
        "unit_close_model_output": "sanitized_before_persistence",
    }
    return StateWriterOutput.model_validate(data)


def _has_boundary_confusion(text: str, method: str) -> bool:
    return method in {"example_comparison", "flawed_interpretation_critic", "review_point_runner", "no_ai_reconstruction_tester"} or any(
        marker in text for marker in ("区别", "是不是", "是否等同", "一定是", "等同", "和", " vs ")
    )


def _mentions_derivation(text: str) -> bool:
    lowered = text.lower()
    return any(marker in text for marker in ("推导", "证明", "不信", "不放心")) or any(marker in lowered for marker in ("derive", "derivation", "prove", "trust"))

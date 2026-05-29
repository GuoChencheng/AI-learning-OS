from __future__ import annotations

import os
from time import perf_counter
from typing import Any

from ailearn.assessment.claim import ClaimEpistemicEvaluator
from ailearn.assessment.derivation import DerivationTrustEvaluator
from ailearn.assessment.distinction import DistinctionTestEvaluator
from ailearn.assessment.misconception import MisconceptionTracker, misconception_key
from ailearn.assessment.no_ai import NoAITestEvaluator
from ailearn.agents.contracts import ContextExtractorOutput
from ailearn.agents.model_backed import ModelBackedAnswerComposerAgent, ModelBackedStateWriterAgent
from ailearn.agents.deterministic import (
    ContextExtractorAgent,
    ContextPackBuilderAgent,
    ProjectResolverAgent,
    RequestIntakeAgent,
    StateJudgeAgent,
)
from ailearn.db.repository import Repository
from ailearn.learning_units.distiller import LearningUnitCloseDistiller
from ailearn.learning_units.manager import LearningUnitManager
from ailearn.model_gateway.base import ModelGateway
from ailearn.model_gateway.fake import FakeModelGateway
from ailearn.modules.router import ModuleRouter, ModuleRoutingInput
from ailearn.state_writer.service import StateWriterService


PIPELINE_AGENTS = [
    "request_intake",
    "project_resolver",
    "context_extractor",
    "context_pack_builder",
    "state_judge",
    "module_router",
    "answer_composer",
    "state_writer",
]


class ChatOrchestrator:
    def __init__(self, repository: Repository, model_gateway: ModelGateway | None = None) -> None:
        self.repository = repository
        self.model_gateway = model_gateway or FakeModelGateway()

    def run(self, project_id: str | None, message: str, selected_mode: str = "auto", button_action: str | None = None) -> dict[str, Any]:
        trace: dict[str, Any] = {"steps": []}
        request_intake = RequestIntakeAgent().run(message, selected_mode, button_action)
        trace["steps"].append(_step("request_intake", request_intake))

        resolver = ProjectResolverAgent().run(project_id, self.repository)
        trace["steps"].append(_step("project_resolver", resolver))
        project_id = resolver.project_id
        project_settings = self.repository.ensure_project_settings(project_id)
        user_message = self.repository.add_message(project_id, "user", message, selected_mode, button_action)

        unit_decision = LearningUnitManager().resolve_for_chat(project_id, message, selected_mode, button_action, self.repository)
        unit = self.repository.get_by_id("learning_units", unit_decision.unit_id) if unit_decision.unit_id else None
        if unit_decision.should_run_full_context_extraction:
            extracted = ContextExtractorAgent().run(project_id, self.repository, message)
            trace["steps"].append(_step("context_extractor", extracted))
            pack = ContextPackBuilderAgent().run(message, request_intake, extracted)
        else:
            extracted = _extracted_from_unit(unit)
            trace["steps"].append(_step("context_extractor", {"skipped": True, "reason": unit_decision.reason}))
            pack = ContextPackBuilderAgent().run_from_learning_unit(
                message,
                request_intake,
                unit or {},
                self.repository.list_learning_unit_turns(unit["id"]) if unit else [],
            )
        context_pack_persisted = _debug_persist_context_enabled()
        if context_pack_persisted:
            self.repository.add_context_pack(project_id, user_message["id"], pack.model_dump(mode="json"))
        trace["steps"].append(_step("context_pack_builder", pack))

        judge = StateJudgeAgent().run(pack, extracted)
        trace["steps"].append(_step("state_judge", judge))

        state_recommendation = "review" if judge.learning_state == "needs_review" else pack.suggested_learning_action
        routing = ModuleRouter().route(
            ModuleRoutingInput(
                button_action=button_action,
                selected_mode=selected_mode,
                unit_method_override=unit_decision.method_override,
                project_default_mode=project_settings.get("default_learning_action"),
                state_recommendation=state_recommendation,
            )
        )
        trace["steps"].append(_step("module_router", routing))

        close_distillation: dict[str, Any] | None = None
        if unit_decision.close_unit_id and unit_decision.action != "no_unit":
            close_distillation = LearningUnitCloseDistiller(self.model_gateway).distill_and_close(
                project_id,
                unit_decision.close_unit_id,
                unit_decision.close_reason or "unit_closed",
                self.repository,
            )

        if unit_decision.action in {"create_new_unit", "close_and_create_new"}:
            unit = self.repository.create_learning_unit(
                project_id,
                routing.module,
                unit_decision.topic or request_intake.topic,
                user_message["id"],
                {
                    "context_pack": pack.model_dump(mode="json"),
                    "context_extractor": extracted.model_dump(mode="json"),
                    "created_from_message_id": user_message["id"],
                },
            )
        elif unit_decision.action == "refresh_unit_context" and unit:
            unit = self.repository.update_learning_unit(
                unit["id"],
                {
                    "context_snapshot_json": {
                        "context_pack": pack.model_dump(mode="json"),
                        "context_extractor": extracted.model_dump(mode="json"),
                        "created_from_message_id": unit.get("start_message_id"),
                        "refreshed_from_message_id": user_message["id"],
                        "refresh_requested": False,
                    }
                },
            )
        if unit:
            self.repository.add_learning_unit_turn(
                unit["id"],
                project_id,
                user_message["id"],
                "user",
                message[:240],
                {"selected_mode": selected_mode, "button_action": button_action, "learning_unit_action": unit_decision.action},
            )

        started = perf_counter()
        answer_composer = ModelBackedAnswerComposerAgent(self.model_gateway)
        answer = answer_composer.run(
            routing.module,
            pack,
            judge,
            active_unit=unit,
            project_settings=project_settings,
            system_settings=self.repository.get_system_settings(),
        )
        latency_ms = int((perf_counter() - started) * 1000)
        assistant_message = self.repository.add_message(project_id, "assistant", answer.answer, selected_mode, button_action)
        if unit:
            self.repository.add_learning_unit_turn(unit["id"], project_id, assistant_message["id"], "assistant", answer.answer[:240], None)
        self.repository.add_module_run(project_id, user_message["id"], routing.module, message[:240], answer.answer[:240], "strong", latency_ms)
        trace["steps"].append(_step("answer_composer", answer))

        state_writer = ModelBackedStateWriterAgent(self.model_gateway).run(
            project_id,
            message,
            answer,
            pack,
            judge,
            routing.module,
            user_message["id"],
            active_unit=unit,
        )
        state_updates = StateWriterService(self.repository).apply(project_id, user_message["id"], state_writer)
        assessment_updates = self._run_turn_assessments(
            project_id,
            message,
            routing.module,
            pack.model_dump(mode="json"),
            state_updates,
            unit,
            user_message["id"],
        )
        trace["steps"].append(_step("state_writer", state_writer))
        if assessment_updates:
            trace["assessment"] = assessment_updates
        trace["message_ids"] = {"user": user_message["id"], "assistant": assistant_message["id"]}
        trace["debug"] = {"context_pack_persisted": context_pack_persisted}
        if unit and unit_decision.action == "no_unit":
            close_distillation = LearningUnitCloseDistiller(self.model_gateway).distill_and_close(
                project_id,
                unit["id"],
                unit_decision.close_reason or "user_requested_close",
                self.repository,
            )
            unit = close_distillation["unit"]
        active_unit = self.repository.get_active_learning_unit(project_id)
        if close_distillation:
            trace["unit_close_distillation"] = {
                "unit_id": close_distillation["unit"]["id"],
                "close_reason": close_distillation["unit"].get("close_reason"),
                "state_update_log_id": close_distillation["state_updates"].get("log_id"),
            }
        trace["learning_unit"] = {
            "id": unit["id"] if unit else None,
            "action": unit_decision.action,
            "method": (active_unit or unit or {}).get("method") if unit else None,
            "topic": (active_unit or unit or {}).get("topic") if unit else unit_decision.topic,
            "turn_count": (active_unit or unit or {}).get("turn_count", 0) if unit else 0,
            "should_run_full_context_extraction": unit_decision.should_run_full_context_extraction,
            "reason": unit_decision.reason,
        }

        return {
            "answer": answer.answer,
            "suggested_next_action": answer.suggested_next_action,
            "pipeline_trace": trace,
            "state_updates": {
                "claims": state_updates["claims"],
                "distinctions": state_updates["distinctions"],
                "temporal_traces": state_updates["temporal_traces"],
                "review_triggers": state_updates["review_triggers"],
                "knowledge_positions": state_updates["knowledge_positions"],
                "derivation_trust_records": state_updates["derivation_trust_records"],
                "assessments": assessment_updates,
                "user_originated_updates": state_updates.get("user_originated_updates", {}),
                "log_id": state_updates["log_id"],
            },
            "active_learning_unit": active_unit,
            "model_path": answer_composer.last_model_path,
        }

    def _run_turn_assessments(
        self,
        project_id: str,
        message: str,
        module_name: str,
        context_pack: dict[str, Any],
        state_updates: dict[str, Any],
        active_unit: dict[str, Any] | None,
        source_message_id: str,
    ) -> dict[str, Any]:
        assessments: dict[str, Any] = {}

        claim_assessments: list[dict[str, Any]] = []
        for claim in state_updates.get("claims", []):
            result = ClaimEpistemicEvaluator().evaluate(project_id, claim, message, context_pack, self.model_gateway)
            if result.claim_id:
                self.repository.update_claim_epistemic_status(result.claim_id, result.model_dump(mode="json"))
            claim_assessments.append(result.model_dump(mode="json"))
            if result.status in {"wrong", "misleading"} or _contains_misconception_pattern(message):
                misconception = MisconceptionTracker().record_or_update(
                    project_id,
                    message,
                    [result.claim_id] if result.claim_id else [],
                    [],
                    result.evidence_text,
                    self.repository,
                )
                assessments["misconception"] = misconception
        if claim_assessments:
            assessments["claim_epistemic"] = claim_assessments

        if _contains_misconception_pattern(message) and "misconception" not in assessments:
            assessments["misconception"] = MisconceptionTracker().record_or_update(
                project_id,
                message,
                [claim["id"] for claim in state_updates.get("claims", []) if claim.get("id")],
                [item["id"] for item in state_updates.get("distinctions", []) if item.get("id")],
                message,
                self.repository,
            )

        if module_name == "no_ai_reconstruction_tester" or (active_unit and active_unit.get("method") == "no_ai_reconstruction_tester"):
            concept = _assessment_topic(active_unit, message)
            current = _latest_knowledge_position(self.repository.project_state(project_id).get("knowledge_positions", []), concept)
            result = NoAITestEvaluator().evaluate(project_id, concept, message, current or {"current_level": "A0"}, context_pack, self.model_gateway)
            updated = self.repository.update_knowledge_position_assessment(
                project_id,
                result.concept,
                result.previous_level,
                result.new_level,
                result.result,
                result.evidence_text,
                result.reason,
            )
            self.repository.log_assessment_update(
                project_id,
                source_message_id,
                "no_ai_assessment",
                {"result": result.model_dump(mode="json"), "knowledge_position_id": updated["id"]},
            )
            assessments["no_ai"] = result.model_dump(mode="json")

        derivations = list(state_updates.get("derivation_trust_records", []))
        if module_name == "derivation_coach" or (active_unit and active_unit.get("method") == "derivation_coach"):
            if not derivations:
                derivations = self.repository.project_state(project_id).get("derivation_trust_records", [])[:1]
            if derivations:
                result = DerivationTrustEvaluator().evaluate_step(project_id, derivations[0]["id"], message, self.model_gateway, self.repository)
                assessments["derivation"] = result.model_dump(mode="json")

        if module_name in {"example_comparison", "flawed_interpretation_critic", "review_point_runner"} and not _is_question(message):
            distinctions = list(state_updates.get("distinctions", [])) or self.repository.project_state(project_id).get("distinctions", [])[:1]
            if distinctions:
                result = DistinctionTestEvaluator().evaluate(project_id, distinctions[0]["id"], message, self.model_gateway, self.repository)
                assessments["distinction"] = result.model_dump(mode="json")

        return assessments


def _step(agent: str, output: Any) -> dict[str, Any]:
    return {"agent": agent, "output": output.model_dump(mode="json") if hasattr(output, "model_dump") else output}


def _debug_persist_context_enabled() -> bool:
    return os.getenv("AI_LEARN_DEBUG_PERSIST_CONTEXT", "").strip().lower() in {"1", "true", "yes", "on"}


def _extracted_from_unit(unit: dict[str, Any] | None) -> ContextExtractorOutput:
    if unit:
        snapshot = unit.get("context_snapshot_json") if isinstance(unit.get("context_snapshot_json"), dict) else {}
        extracted = snapshot.get("context_extractor") if isinstance(snapshot, dict) else None
        if isinstance(extracted, dict):
            return ContextExtractorOutput.model_validate(extracted)
    return ContextExtractorOutput(
        relevant_goals=[],
        relevant_references=[],
        relevant_reference_chunks=[],
        relevant_claims=[],
        relevant_distinctions=[],
        recent_traces=[],
        active_review_triggers=[],
    )


def _summarize_unit_close(unit: dict[str, Any], message: str, answer: str) -> str:
    return f"{unit.get('method', 'learning')} unit on {unit.get('topic', 'current topic')} was closed after: {message[:120]}. Last response: {answer[:160]}"


def _contains_misconception_pattern(message: str) -> bool:
    key = misconception_key(message)
    return not key.startswith("misc_")


def _assessment_topic(unit: dict[str, Any] | None, message: str) -> str:
    if unit and unit.get("topic"):
        return str(unit["topic"])
    cleaned = " ".join(message.strip().split())
    return cleaned[:80].rstrip(" ?？。.") or "current no-AI target"


def _latest_knowledge_position(positions: list[dict[str, Any]], concept: str) -> dict[str, Any] | None:
    for position in positions:
        if position.get("concept") == concept:
            return position
    return positions[0] if positions else None


def _is_question(message: str) -> bool:
    lowered = message.lower()
    return "?" in message or "？" in message or any(marker in message for marker in ("什么", "为什么", "吗", "是否", "是不是")) or lowered.startswith(("what", "why", "how", "is ", "are "))

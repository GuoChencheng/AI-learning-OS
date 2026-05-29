from __future__ import annotations

import os
from time import perf_counter
from typing import Any

from ailearn.agents.contracts import ContextExtractorOutput
from ailearn.agents.deterministic import (
    AnswerComposerAgent,
    ContextExtractorAgent,
    ContextPackBuilderAgent,
    ProjectResolverAgent,
    RequestIntakeAgent,
    StateJudgeAgent,
    StateWriterAgent,
)
from ailearn.db.repository import Repository
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
        answer = AnswerComposerAgent().run(routing.module, pack, judge)
        latency_ms = int((perf_counter() - started) * 1000)
        assistant_message = self.repository.add_message(project_id, "assistant", answer.answer, selected_mode, button_action)
        if unit:
            self.repository.add_learning_unit_turn(unit["id"], project_id, assistant_message["id"], "assistant", answer.answer[:240], None)
        self.repository.add_module_run(project_id, user_message["id"], routing.module, message[:240], answer.answer[:240], "fast", latency_ms)
        trace["steps"].append(_step("answer_composer", answer))

        state_writer = StateWriterAgent().run(project_id, message, answer, pack, judge, routing.module, user_message["id"])
        state_updates = StateWriterService(self.repository).apply(project_id, user_message["id"], state_writer)
        trace["steps"].append(_step("state_writer", state_writer))
        trace["message_ids"] = {"user": user_message["id"], "assistant": assistant_message["id"]}
        trace["debug"] = {"context_pack_persisted": context_pack_persisted}
        if unit and unit_decision.action == "no_unit":
            self.repository.update_learning_unit(unit["id"], {"unit_summary": _summarize_unit_close(unit, message, answer.answer)})
            unit = self.repository.close_learning_unit(unit["id"], "user_requested_close")
        active_unit = self.repository.get_active_learning_unit(project_id)
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
                "log_id": state_updates["log_id"],
            },
            "active_learning_unit": active_unit,
        }


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
        relevant_claims=[],
        relevant_distinctions=[],
        recent_traces=[],
        active_review_triggers=[],
    )


def _summarize_unit_close(unit: dict[str, Any], message: str, answer: str) -> str:
    return f"{unit.get('method', 'learning')} unit on {unit.get('topic', 'current topic')} was closed after: {message[:120]}. Last response: {answer[:160]}"

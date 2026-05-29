from __future__ import annotations

from time import perf_counter
from typing import Any

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

        extracted = ContextExtractorAgent().run(project_id, self.repository)
        trace["steps"].append(_step("context_extractor", extracted))

        pack = ContextPackBuilderAgent().run(message, request_intake, extracted)
        self.repository.add_context_pack(project_id, user_message["id"], pack.model_dump(mode="json"))
        trace["steps"].append(_step("context_pack_builder", pack))

        judge = StateJudgeAgent().run(pack, extracted)
        trace["steps"].append(_step("state_judge", judge))

        state_recommendation = "review" if judge.learning_state == "needs_review" else pack.suggested_learning_action
        routing = ModuleRouter().route(
            ModuleRoutingInput(
                button_action=button_action,
                selected_mode=selected_mode,
                project_default_mode=project_settings.get("default_learning_action"),
                state_recommendation=state_recommendation,
            )
        )
        trace["steps"].append(_step("module_router", routing))

        started = perf_counter()
        answer = AnswerComposerAgent().run(routing.module, pack, judge)
        latency_ms = int((perf_counter() - started) * 1000)
        assistant_message = self.repository.add_message(project_id, "assistant", answer.answer, selected_mode, button_action)
        self.repository.add_module_run(project_id, user_message["id"], routing.module, message[:240], answer.answer[:240], "fast", latency_ms)
        trace["steps"].append(_step("answer_composer", answer))

        state_writer = StateWriterAgent().run(project_id, message, answer, pack, judge)
        state_updates = StateWriterService(self.repository).apply(project_id, user_message["id"], state_writer)
        trace["steps"].append(_step("state_writer", state_writer))
        trace["message_ids"] = {"user": user_message["id"], "assistant": assistant_message["id"]}

        return {
            "answer": answer.answer,
            "suggested_next_action": answer.suggested_next_action,
            "pipeline_trace": trace,
            "state_updates": {
                "claims": state_updates["claims"],
                "distinctions": state_updates["distinctions"],
                "review_triggers": state_updates["review_triggers"],
                "log_id": state_updates["log_id"],
            },
        }


def _step(agent: str, output: Any) -> dict[str, Any]:
    return {"agent": agent, "output": output.model_dump(mode="json") if hasattr(output, "model_dump") else output}


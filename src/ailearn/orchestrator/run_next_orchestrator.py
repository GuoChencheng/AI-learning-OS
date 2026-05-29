from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ailearn.agents.contracts import AnswerComposerOutput, NewTemporalTrace, StateWriterOutput
from ailearn.agents.deterministic import ContextExtractorAgent, ContextPackBuilderAgent, RequestIntakeAgent
from ailearn.db.repository import Repository
from ailearn.learning_units.distiller import LearningUnitCloseDistiller
from ailearn.model_gateway.base import ModelGateway
from ailearn.model_gateway.fake import FakeModelGateway
from ailearn.state_writer.service import StateWriterService


class RunNextOrchestrator:
    def __init__(self, repository: Repository, model_gateway: ModelGateway | None = None) -> None:
        self.repository = repository
        self.model_gateway = model_gateway or FakeModelGateway()

    def run(self, project_id: str) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        if not project:
            raise KeyError(project_id)
        active_unit = self.repository.get_active_learning_unit(project_id)
        global_decision = self._decide(project_id)
        close_distillation: dict[str, Any] | None = None
        should_run_full_context_extraction = False
        learning_unit_reason = "Run Next created a new learning unit."

        if active_unit and _should_jump_to_global_priority(global_decision, active_unit):
            close_distillation = LearningUnitCloseDistiller(self.model_gateway).distill_and_close(
                project_id,
                active_unit["id"],
                "run_next_global_priority",
                self.repository,
            )
            active_unit = None
            decision = global_decision
            learning_unit_action = "jump_to_global_priority"
            should_run_full_context_extraction = True
            learning_unit_reason = "Run Next jumped to a higher-priority durable learning-state blocker."
        elif active_unit and _refresh_requested(active_unit):
            learning_unit_action = "refresh_active_unit"
            decision = self._continue_unit_decision(active_unit)
            active_unit = self._refresh_unit_context(project_id, active_unit, decision)
            should_run_full_context_extraction = True
            learning_unit_reason = "Run Next refreshed stale working context for the active learning unit."
        elif active_unit and int(active_unit.get("turn_count") or 0) >= 16:
            close_distillation = LearningUnitCloseDistiller(self.model_gateway).distill_and_close(
                project_id,
                active_unit["id"],
                "run_next_max_turns",
                self.repository,
            )
            active_unit = None
            decision = global_decision
            learning_unit_action = "close_active_unit"
            should_run_full_context_extraction = True
            learning_unit_reason = "Run Next closed a stale learning unit and started the next action."
        elif active_unit:
            learning_unit_action = "continue_active_unit"
            decision = self._continue_unit_decision(active_unit)
            learning_unit_reason = "Run Next continues a valid active learning unit."
        else:
            learning_unit_action = "create_new_unit"
            decision = global_decision
            should_run_full_context_extraction = True
        answer = AnswerComposerOutput(
            answer=decision["answer"],
            exercise=None,
            follow_up_question=None,
            suggested_next_action=decision["next_action"],
        )
        message = self.repository.add_message(project_id, "assistant", answer.answer, "auto", "run_next")
        if learning_unit_action in {"create_new_unit", "jump_to_global_priority", "close_active_unit"}:
            active_unit = self._create_run_next_unit(project_id, message["id"], decision)
        if active_unit:
            self.repository.add_learning_unit_turn(active_unit["id"], project_id, message["id"], "assistant", answer.answer[:240], {"run_next_priority": decision["priority"]})
            active_unit = self.repository.get_by_id("learning_units", active_unit["id"])
        writer = StateWriterOutput.model_validate(
            {
                "new_claims": [],
                "updated_claims": [],
                "new_distinctions": [],
                "new_temporal_trace": NewTemporalTrace(
                    event_type="run_next",
                    user_question="/api/run-next",
                    system_response_summary=answer.answer[:240],
                    state_change_summary=f"Run Next chose {decision['chosen_module']}.",
                    next_step=answer.suggested_next_action,
                ).model_dump(),
                "knowledge_position_updates": [],
                "derivation_trust_updates": [],
                "review_triggers": [],
                "next_recommended_action": answer.suggested_next_action,
                "source_metadata": {
                    "source_type": "system_trace",
                    "source_message_id": message["id"],
                    "evidence_text": "/api/run-next selected the next learning action from durable project state.",
                },
                "user_originated_updates": {"temporal_traces": 1},
                "ai_only_observations": {"run_next_priority": decision["priority"]},
                "discarded_ephemeral_judgments": {"run_next_decision": "pipeline_trace_only"},
            }
        )
        state_updates = StateWriterService(self.repository).apply(project_id, message["id"], writer)
        self.repository.add_module_run(project_id, message["id"], decision["chosen_module"], decision["reason"], answer.answer[:240], "fast", 0)
        return {
            "chosen_module": decision["chosen_module"],
            "reason": decision["reason"],
            "answer": answer.answer,
            "pipeline_trace": {
                "decision": decision,
                "steps": [{"agent": "run_next_orchestrator", "output": decision}],
                "learning_unit": {
                    "id": active_unit["id"] if active_unit else None,
                    "action": learning_unit_action,
                    "method": active_unit.get("method") if active_unit else decision["chosen_module"],
                    "topic": active_unit.get("topic") if active_unit else decision["reason"],
                    "turn_count": active_unit.get("turn_count", 0) if active_unit else 0,
                    "should_run_full_context_extraction": should_run_full_context_extraction,
                    "reason": learning_unit_reason,
                    "closed_unit_id": close_distillation["unit"]["id"] if close_distillation else None,
                    "close_state_update_log_id": close_distillation["state_updates"].get("log_id") if close_distillation else None,
                },
            },
            "state_updates": {"temporal_traces": state_updates["temporal_traces"], "log_id": state_updates["log_id"]},
            "priority": decision["priority"],
            "loop_step": decision["loop_step"],
            "why_this_now": decision["why_this_now"],
            "expected_user_action": decision["expected_user_action"],
            "will_update": decision["will_update"],
            "active_learning_unit": active_unit,
        }

    def _continue_unit_decision(self, unit: dict[str, Any]) -> dict[str, Any]:
        topic = unit.get("topic") or "current learning unit"
        method = unit.get("method") or "auto_run_router"
        return {
            "priority": "current_goal_next_action",
            "loop_step": "action",
            "chosen_module": method,
            "reason": f"Continuing active learning unit: {topic}.",
            "why_this_now": "The active learning unit is still valid, so context should be reused instead of re-extracted.",
            "expected_user_action": "Continue the current learning sequence.",
            "will_update": ["temporal_trace", "learning_unit_turn"],
            "answer": f"继续当前学习单元：{topic}。下一步沿用当前方法，先补上你对上一轮问题的判断或例子。",
            "next_action": "继续当前学习单元。",
        }

    def _create_run_next_unit(self, project_id: str, message_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        request = decision["reason"]
        intake = RequestIntakeAgent().run(request, "auto", "run_next")
        extracted = ContextExtractorAgent().run(project_id, self.repository, request)
        pack = ContextPackBuilderAgent().run(request, intake, extracted)
        return self.repository.create_learning_unit(
            project_id,
            decision["chosen_module"],
            decision["reason"],
            message_id,
            {
                "context_pack": pack.model_dump(mode="json"),
                "context_extractor": extracted.model_dump(mode="json"),
                "created_from_message_id": message_id,
                "created_by": "run_next",
            },
        )

    def _refresh_unit_context(self, project_id: str, unit: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        request = unit.get("topic") or decision["reason"]
        intake = RequestIntakeAgent().run(request, "auto", "run_next")
        extracted = ContextExtractorAgent().run(project_id, self.repository, request)
        pack = ContextPackBuilderAgent().run(request, intake, extracted)
        existing = unit.get("context_snapshot_json") if isinstance(unit.get("context_snapshot_json"), dict) else {}
        return self.repository.update_learning_unit(
            unit["id"],
            {
                "context_snapshot_json": {
                    **existing,
                    "context_pack": pack.model_dump(mode="json"),
                    "context_extractor": extracted.model_dump(mode="json"),
                    "refresh_requested": False,
                    "refreshed_by": "run_next",
                }
            },
        )

    def _decide(self, project_id: str) -> dict[str, Any]:
        state = self.repository.project_state(project_id)
        goals = self.repository.list_goal_stacks(project_id, limit=1)
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        due = [item for item in state["review_triggers"] if item.get("status") == "pending" and item.get("scheduled_time", "") <= now]
        if due:
            target = due[0]["target"]
            return {
                "priority": "due_review_trigger",
                "loop_step": "review",
                "chosen_module": "review_point_runner",
                "reason": f"Due Review Trigger for {target}.",
                "why_this_now": "A pending review trigger is due and has the highest run-next priority.",
                "expected_user_action": "Answer the review prompt without AI help, then mark whether it passed.",
                "will_update": ["temporal_trace", "review_trigger_status"],
                "answer": f"我建议先处理到期回看点：{target}。请先无提示复述边界，再用一个例子检验。",
                "next_action": "完成这个回看点并记录是否通过。",
            }
        repeated = [claim for claim in state["claims"] if claim.get("status") == "revised"]
        if repeated:
            return {
                "priority": "repeated_misconception",
                "loop_step": "handle",
                "chosen_module": "flawed_interpretation_critic",
                "reason": "A repeatedly revised claim suggests a recurring misconception.",
                "why_this_now": "Repeated revisions are stronger evidence of a learning blockage than moving to new content.",
                "expected_user_action": "Identify the repeated error pattern and restate the corrected boundary.",
                "will_update": ["temporal_trace"],
                "answer": "先审查最近反复修改的 Claim，找出错误解释的共同结构。",
                "next_action": "把错误模式写成可测试的 Distinction。",
            }
        weak_positions = [item for item in state["knowledge_positions"] if item.get("layer") == "no_ai_internalization" and item.get("current_level") in {"A0", "A1", "A2"}]
        if weak_positions:
            concept = weak_positions[0]["concept"]
            return {
                "priority": "unverified_no_ai_internalization",
                "loop_step": "verify",
                "chosen_module": "no_ai_reconstruction_tester",
                "reason": f"{concept} is in no-AI internalization but below A3.",
                "why_this_now": "A no-AI internalization target is below the usable reconstruction level.",
                "expected_user_action": "Attempt a no-AI explanation and include one counterexample.",
                "will_update": ["temporal_trace"],
                "answer": f"下一步做无 AI 重构测试：请不用提示解释 {concept}，并给出一个反例。",
                "next_action": "根据答案更新 A0-A4。",
            }
        if goals:
            return {
                "priority": "current_goal_next_action",
                "loop_step": "action",
                "chosen_module": "auto_run_router",
                "reason": "No higher priority block; using current Goal Stack next action.",
                "why_this_now": "There is no due review, repeated misconception, or no-AI trust gap ahead of the current goal.",
                "expected_user_action": "Follow the current goal's next action.",
                "will_update": ["temporal_trace"],
                "answer": f"当前目标下一步：{goals[0].get('next_action') or '提出一个最小问题并验证。'}",
                "next_action": goals[0].get("next_action") or "提出一个最小问题并验证。",
            }
        traces = state["temporal_traces"]
        if traces:
            return {
                "priority": "recent_unresolved_question",
                "loop_step": "thought",
                "chosen_module": "socratic_questioner",
                "reason": "Recent trace exists without a higher priority item.",
                "why_this_now": "The recent trace is the only available learner-state evidence for selecting the next action.",
                "expected_user_action": "Answer the Socratic prompt so the blockage can be localized.",
                "will_update": ["temporal_trace"],
                "answer": "基于最近学习轨迹，我建议先回答一个追问来暴露阻滞点。",
                "next_action": "回答追问并写回 Claim。",
            }
        return {
            "priority": "new_knowledge_progress",
            "loop_step": "next_round",
            "chosen_module": "concept_explainer",
            "reason": "No active blocker found; advance with explanation.",
            "why_this_now": "No durable state currently indicates a higher-priority review or repair action.",
            "expected_user_action": "Ask the next concrete learning question.",
            "will_update": ["temporal_trace"],
            "answer": "当前没有到期回看或明显阻滞。建议推进一个新知识点，并同步记录最小 Claim。",
            "next_action": "提出下一个学习问题。",
        }


def _refresh_requested(unit: dict[str, Any]) -> bool:
    snapshot = unit.get("context_snapshot_json") if isinstance(unit.get("context_snapshot_json"), dict) else {}
    return bool(snapshot.get("refresh_requested"))


def _should_jump_to_global_priority(decision: dict[str, Any], active_unit: dict[str, Any]) -> bool:
    if decision.get("priority") not in {"due_review_trigger", "repeated_misconception", "unverified_no_ai_internalization"}:
        return False
    if decision.get("chosen_module") == active_unit.get("method"):
        return False
    return True

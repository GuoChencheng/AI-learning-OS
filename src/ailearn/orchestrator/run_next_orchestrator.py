from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ailearn.agents.contracts import AnswerComposerOutput, NewTemporalTrace, StateWriterOutput
from ailearn.db.repository import Repository
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
        decision = self._decide(project_id)
        answer = AnswerComposerOutput(
            answer=decision["answer"],
            exercise=None,
            follow_up_question=None,
            suggested_next_action=decision["next_action"],
        )
        message = self.repository.add_message(project_id, "assistant", answer.answer, "auto", "run_next")
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
            }
        )
        state_updates = StateWriterService(self.repository).apply(project_id, message["id"], writer)
        self.repository.add_module_run(project_id, message["id"], decision["chosen_module"], decision["reason"], answer.answer[:240], "fast", 0)
        return {
            "chosen_module": decision["chosen_module"],
            "reason": decision["reason"],
            "answer": answer.answer,
            "pipeline_trace": {"decision": decision, "steps": [{"agent": "run_next_orchestrator", "output": decision}]},
            "state_updates": {"temporal_traces": state_updates["temporal_traces"], "log_id": state_updates["log_id"]},
        }

    def _decide(self, project_id: str) -> dict[str, Any]:
        state = self.repository.project_state(project_id)
        goals = self.repository.list_goal_stacks(project_id, limit=1)
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        due = [item for item in state["review_triggers"] if item.get("status") == "pending" and item.get("scheduled_time", "") <= now]
        if due:
            target = due[0]["target"]
            return {
                "priority": "due_review_trigger",
                "chosen_module": "review_point_runner",
                "reason": f"Due Review Trigger for {target}.",
                "answer": f"我建议先处理到期回看点：{target}。请先无提示复述边界，再用一个例子检验。",
                "next_action": "完成这个回看点并记录是否通过。",
            }
        repeated = [claim for claim in state["claims"] if claim.get("status") == "revised"]
        if repeated:
            return {
                "priority": "repeated_misconception",
                "chosen_module": "flawed_interpretation_critic",
                "reason": "A repeatedly revised claim suggests a recurring misconception.",
                "answer": "先审查最近反复修改的 Claim，找出错误解释的共同结构。",
                "next_action": "把错误模式写成可测试的 Distinction。",
            }
        weak_positions = [item for item in state["knowledge_positions"] if item.get("layer") == "no_ai_internalization" and item.get("current_level") in {"A0", "A1", "A2"}]
        if weak_positions:
            concept = weak_positions[0]["concept"]
            return {
                "priority": "unverified_no_ai_internalization",
                "chosen_module": "no_ai_reconstruction_tester",
                "reason": f"{concept} is in no-AI internalization but below A3.",
                "answer": f"下一步做无 AI 重构测试：请不用提示解释 {concept}，并给出一个反例。",
                "next_action": "根据答案更新 A0-A4。",
            }
        if goals:
            return {
                "priority": "current_goal_next_action",
                "chosen_module": "auto_run_router",
                "reason": "No higher priority block; using current Goal Stack next action.",
                "answer": f"当前目标下一步：{goals[0].get('next_action') or '提出一个最小问题并验证。'}",
                "next_action": goals[0].get("next_action") or "提出一个最小问题并验证。",
            }
        traces = state["temporal_traces"]
        if traces:
            return {
                "priority": "recent_unresolved_question",
                "chosen_module": "socratic_questioner",
                "reason": "Recent trace exists without a higher priority item.",
                "answer": "基于最近学习轨迹，我建议先回答一个追问来暴露阻滞点。",
                "next_action": "回答追问并写回 Claim。",
            }
        return {
            "priority": "new_knowledge_progress",
            "chosen_module": "concept_explainer",
            "reason": "No active blocker found; advance with explanation.",
            "answer": "当前没有到期回看或明显阻滞。建议推进一个新知识点，并同步记录最小 Claim。",
            "next_action": "提出下一个学习问题。",
        }


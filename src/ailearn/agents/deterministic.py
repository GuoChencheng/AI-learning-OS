from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .contracts import (
    AnswerComposerOutput,
    ContextExtractorOutput,
    ContextPackBuilderOutput,
    NewClaim,
    NewDistinction,
    NewReviewTrigger,
    NewTemporalTrace,
    ProjectResolverOutput,
    RequestIntakeOutput,
    StateJudgeOutput,
    StateWriterOutput,
)


def _topic_from_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "current learning topic"
    return cleaned[:80].rstrip(" ?？。.")


class RequestIntakeAgent:
    def run(self, message: str, selected_mode: str = "auto", button_action: str | None = None) -> RequestIntakeOutput:
        mode = button_action or selected_mode or "auto"
        intent = "ask_concept"
        lowered = message.lower()
        if mode == "derive" or "derive" in lowered or "推导" in message:
            intent = "derive"
        elif mode == "exercise" or "出题" in message or "exercise" in lowered:
            intent = "do_exercise"
        elif mode == "review" or "回看" in message or "review" in lowered:
            intent = "review"
        elif "plan" in lowered or "计划" in message:
            intent = "ask_plan"
        return RequestIntakeOutput.model_validate(
            {
                "intent": intent,
                "topic": _topic_from_text(message),
                "urgency": "medium" if "?" in message or "？" in message else "low",
                "needs_reference": True,
                "needs_state_read": True,
                "user_selected_mode": mode if mode in {"explain", "compare", "socratic", "derive", "exercise", "critic", "review", "auto"} else "auto",
            }
        )


class ProjectResolverAgent:
    def run(self, project_id: str | None, repository: Any) -> ProjectResolverOutput:
        if project_id and repository.get_project(project_id):
            return ProjectResolverOutput(project_id=project_id, confidence=1.0, reason="Request supplied an existing project id.")
        project = repository.ensure_default_project()
        return ProjectResolverOutput(project_id=project["id"], confidence=0.55, reason="No valid project supplied; using the default local project.")


class ContextExtractorAgent:
    def run(self, project_id: str, repository: Any) -> ContextExtractorOutput:
        state = repository.project_state(project_id)
        return ContextExtractorOutput.model_validate(
            {
                "relevant_goals": repository.list_goal_stacks(project_id, limit=1),
                "relevant_references": repository.list_references(project_id, limit=5),
                "relevant_claims": state["claims"][:5],
                "relevant_distinctions": state["distinctions"][:5],
                "recent_traces": state["temporal_traces"][:10],
                "active_review_triggers": [item for item in state["review_triggers"] if item.get("status") == "pending"][:10],
            }
        )


class ContextPackBuilderAgent:
    def run(self, request: str, intake: RequestIntakeOutput, extracted: ContextExtractorOutput) -> ContextPackBuilderOutput:
        known_confusions = [
            f"{item.get('concept_a', '')} vs {item.get('concept_b', '')}".strip()
            for item in extracted.relevant_distinctions
            if item.get("concept_a") and item.get("concept_b")
        ]
        reference_titles = [item.get("title", "") for item in extracted.relevant_references if item.get("title")]
        action = "explain"
        if intake.user_selected_mode in {"compare", "socratic", "derive", "exercise", "critic", "review"}:
            action = intake.user_selected_mode
        elif known_confusions:
            action = "compare"
        return ContextPackBuilderOutput.model_validate(
            {
                "current_request": request,
                "goal_context": "; ".join(item.get("current_focus") or item.get("main_goal", "") for item in extracted.relevant_goals) or "No active goal stack yet.",
                "reference_context": "; ".join(reference_titles) or "No selected references.",
                "learning_state_context": f"{len(extracted.relevant_claims)} active claims, {len(extracted.relevant_distinctions)} distinctions, {len(extracted.active_review_triggers)} review triggers.",
                "known_confusions": known_confusions,
                "must_respect_constraints": [
                    "Do not treat AI output as proof of understanding.",
                    "Do not send learner data to a provider without explicit action.",
                    "Use learning-state records, not a static world knowledge graph.",
                ],
                "suggested_learning_action": action,
                "ai_permission_boundary": "guided_hint" if action == "socratic" else "direct_answer",
            }
        )


class StateJudgeAgent:
    def run(self, pack: ContextPackBuilderOutput, extracted: ContextExtractorOutput) -> StateJudgeOutput:
        due_reviews = [item for item in extracted.active_review_triggers if item.get("scheduled_time", "") <= datetime.now(UTC).isoformat()]
        if due_reviews:
            state = "needs_review"
        elif pack.known_confusions:
            state = "confused"
        elif "derive" in pack.current_request.lower() or "推导" in pack.current_request:
            state = "ready_for_derivation"
        else:
            state = "progressing"
        return StateJudgeOutput(
            learning_state=state,
            knowledge_layer="no_ai_internalization" if state in {"confused", "ready_for_derivation", "needs_review"} else "positioning",
            record_intensity="medium" if state in {"confused", "needs_review"} else "light",
            risk_flags=["review_due"] if due_reviews else [],
        )


class AnswerComposerAgent:
    def run(self, module_name: str, pack: ContextPackBuilderOutput, judge: StateJudgeOutput) -> AnswerComposerOutput:
        topic = _topic_from_text(pack.current_request)
        if module_name == "example_comparison":
            answer = f"先把两个概念分开：{topic} 里最关键的是边界条件、适用假设和反例。不要把相邻概念因为经常一起出现就合并成同一个判断。"
            next_action = "做一个概念边界辨析题。"
        elif module_name == "socratic_questioner":
            answer = f"我先不直接替你完成结论。请你先回答：在 {topic} 中，哪些条件是你认为必需的，哪些只是常见但不必然的背景？"
            next_action = "回答这个追问后再写回 Claim。"
        elif module_name == "derivation_coach":
            answer = f"我们按推导信任来处理 {topic}：先列假设，再标出关键步骤，最后区分你能独立重构的步骤和需要 AI 提示的步骤。"
            next_action = "补一条推导信任记录并安排无 AI 重构。"
        elif module_name == "exercise_generator":
            answer = f"题目：不用 AI，给出 {topic} 的一个正例、一个反例，以及你判断二者边界的理由。"
            next_action = "提交答案后进入改错循环。"
        elif module_name == "review_point_runner":
            answer = f"回看优先：请先复述 {topic} 的核心边界，再用一个新例子检验它。"
            next_action = "完成回看点并标记是否通过。"
        elif module_name == "no_ai_reconstruction_tester":
            answer = f"无 AI 测试：关掉提示后，用 5 句话重构 {topic}。必须包含定义、边界、反例、一个应用场景和一个仍不确定的问题。"
            next_action = "根据无 AI 表现更新 A0-A4 内化等级。"
        elif module_name == "flawed_interpretation_critic":
            answer = f"审查角度：检查 {topic} 里是否有把类比当事实、把常见条件当定理、或把学习策略当学科结论的错误。"
            next_action = "把发现的错误写为 Claim 修正或 Distinction。"
        else:
            answer = f"简要解释：{topic} 需要按学习状态处理，而不是只存成百科知识。先给出可用理解，再标记假设、边界和下一步验证。"
            next_action = "写回一条轻量 Claim，并安排一个小回看点。"
        return AnswerComposerOutput(answer=answer, exercise=None, follow_up_question=None, suggested_next_action=next_action)


class StateWriterAgent:
    def run(self, project_id: str, message: str, answer: AnswerComposerOutput, pack: ContextPackBuilderOutput, judge: StateJudgeOutput) -> StateWriterOutput:
        scheduled = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        topic = _topic_from_text(message)
        return StateWriterOutput.model_validate(
            {
                "new_claims": [
                    NewClaim(
                        original_statement=message,
                        normalized_statement=f"Learning question about {topic}",
                        related_concept=topic,
                        epistemic_status="open_question" if "?" in message or "？" in message else "learning_strategy",
                        confidence=0.45,
                        correction=answer.answer[:500],
                    ).model_dump()
                ],
                "updated_claims": [],
                "new_distinctions": [
                    NewDistinction(
                        concept_a=topic,
                        concept_b="nearby concept or hidden assumption",
                        boundary="Track the assumption boundary explicitly before treating the idea as learned.",
                        common_confusion="Treating a useful explanation as verified understanding.",
                        example="A direct answer feels clear, but the learner cannot reconstruct it without AI.",
                        test_question="What assumption would make this explanation fail?",
                    ).model_dump()
                ],
                "new_temporal_trace": NewTemporalTrace(
                    event_type="chat",
                    user_question=message,
                    system_response_summary=answer.answer[:240],
                    state_change_summary=f"Recorded {judge.record_intensity} learning-state update.",
                    next_step=answer.suggested_next_action,
                ).model_dump(),
                "knowledge_position_updates": [],
                "derivation_trust_updates": [],
                "review_triggers": [
                    NewReviewTrigger(
                        target=topic,
                        trigger_reason="New chat turn created a claim/distinction that should be checked later.",
                        review_type="distinguish",
                        scheduled_time=scheduled,
                        success_criteria="Learner can explain the boundary without AI.",
                    ).model_dump()
                ],
                "next_recommended_action": answer.suggested_next_action,
            }
        )


from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .contracts import (
    AnswerComposerOutput,
    ContextExtractorOutput,
    ContextPackBuilderOutput,
    DerivationTrustUpdate,
    KnowledgePositionUpdate,
    NewClaim,
    NewDistinction,
    NewReviewTrigger,
    NewTemporalTrace,
    ProjectResolverOutput,
    RequestIntakeOutput,
    StateJudgeOutput,
    StateWriterOutput,
)
from ailearn.context_ranking import rank_records


def _topic_from_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "current learning topic"
    return cleaned[:80].rstrip(" ?？。.")


def _action_from_module(module_name: str) -> str:
    return {
        "concept_explainer": "explain",
        "example_comparison": "compare",
        "socratic_questioner": "socratic",
        "derivation_coach": "derive",
        "exercise_generator": "exercise",
        "exercise_correction_loop": "exercise",
        "flawed_interpretation_critic": "critic",
        "review_point_runner": "review",
        "no_ai_reconstruction_tester": "review",
        "auto_run_router": "explain",
    }.get(module_name, "explain")


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
    def run(self, project_id: str, repository: Any, request: str = "") -> ContextExtractorOutput:
        state = repository.project_state(project_id)
        pending_reviews = [item for item in state["review_triggers"] if item.get("status") == "pending"]
        relevant_references = rank_records(repository.list_references(project_id, limit=20), request, "reference", 5)
        relevant_chunks = _select_reference_chunks(repository, relevant_references, request)
        return ContextExtractorOutput.model_validate(
            {
                "relevant_goals": rank_records(repository.list_goal_stacks(project_id, limit=20), request, "goal", 3),
                "relevant_references": relevant_references,
                "relevant_reference_chunks": relevant_chunks,
                "relevant_claims": rank_records(state["claims"], request, "claim", 5),
                "relevant_distinctions": rank_records(state["distinctions"], request, "distinction", 5),
                "recent_traces": rank_records(state["temporal_traces"], request, "temporal_trace", 10),
                "active_review_triggers": rank_records(pending_reviews, request, "review_trigger", 10),
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
        reference_context = _format_reference_context(extracted.relevant_reference_chunks, reference_titles)
        action = "explain"
        if intake.user_selected_mode in {"compare", "socratic", "derive", "exercise", "critic", "review"}:
            action = intake.user_selected_mode
        elif known_confusions:
            action = "compare"
        return ContextPackBuilderOutput.model_validate(
            {
                "current_request": request,
                "goal_context": "; ".join(item.get("current_focus") or item.get("main_goal", "") for item in extracted.relevant_goals) or "No active goal stack yet.",
                "reference_context": reference_context,
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

    def run_from_learning_unit(
        self,
        request: str,
        intake: RequestIntakeOutput,
        unit: dict[str, Any],
        turns: list[dict[str, Any]],
    ) -> ContextPackBuilderOutput:
        snapshot = unit.get("context_snapshot_json") if isinstance(unit.get("context_snapshot_json"), dict) else {}
        base_pack = snapshot.get("context_pack", {}) if isinstance(snapshot, dict) else {}
        method = str(unit.get("method") or "concept_explainer")
        recent_turns = " | ".join(
            f"{turn.get('role', 'turn')}: {turn.get('turn_summary', '')}" for turn in turns[-6:] if turn.get("turn_summary")
        )
        learning_state_parts = [
            f"Learning unit topic: {unit.get('topic') or intake.topic}.",
            f"Learning unit method: {method}.",
        ]
        if unit.get("unit_summary"):
            learning_state_parts.append(f"Unit summary: {unit['unit_summary']}.")
        if recent_turns:
            learning_state_parts.append(f"Recent unit turns: {recent_turns}.")
        action = _action_from_module(method)
        if intake.user_selected_mode in {"compare", "socratic", "derive", "exercise", "critic", "review"}:
            action = intake.user_selected_mode
        return ContextPackBuilderOutput.model_validate(
            {
                "current_request": request,
                "goal_context": base_pack.get("goal_context") or "Reusing the active learning unit context.",
                "reference_context": base_pack.get("reference_context") or "Reusing references selected at unit start.",
                "learning_state_context": " ".join(learning_state_parts),
                "known_confusions": list(base_pack.get("known_confusions") or []),
                "must_respect_constraints": list(
                    base_pack.get("must_respect_constraints")
                    or [
                        "Learning unit context is working memory, not durable learner memory.",
                        "Do not treat AI output as proof of understanding.",
                    ]
                ),
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
    def run(
        self,
        project_id: str,
        message: str,
        answer: AnswerComposerOutput,
        pack: ContextPackBuilderOutput,
        judge: StateJudgeOutput,
        module_name: str = "concept_explainer",
        source_message_id: str | None = None,
    ) -> StateWriterOutput:
        scheduled = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        topic = _topic_from_text(message)
        source_metadata = {
            "source_type": _source_type_for_message(message),
            "source_message_id": source_message_id,
            "evidence_text": _evidence_text(message),
        }
        should_claim = _should_write_claim(message)
        should_distinguish = _has_boundary_confusion(message, pack, judge, module_name)
        should_review = _should_write_review_trigger(message, judge, module_name, should_distinguish)
        should_position = _should_write_knowledge_position(message, judge, module_name)
        should_derivation = _should_write_derivation_trust(message, judge, module_name)

        claims = []
        if should_claim:
            claims.append(
                NewClaim(
                    original_statement=message,
                    normalized_statement=f"Learner-side question or claim about {topic}",
                    related_concept=topic,
                    epistemic_status="open_question" if _is_question(message) else "learning_strategy",
                    confidence=0.45,
                    correction=answer.answer[:500],
                ).model_dump()
            )

        distinctions = []
        if should_distinguish:
            concept_a, concept_b = _split_boundary_concepts(message, topic)
            distinctions.append(
                NewDistinction(
                    concept_a=concept_a,
                    concept_b=concept_b,
                    boundary="Keep the learner's stated boundary question explicit before marking the concept as understood.",
                    common_confusion="Treating nearby concepts, common co-occurrence, or useful explanations as equivalence.",
                    example="A critical point can motivate a CFT description without making every critical point automatically a CFT.",
                    test_question="What condition or counterexample would make the equivalence fail?",
                ).model_dump()
            )

        review_triggers = []
        if should_review:
            review_triggers.append(
                NewReviewTrigger(
                    target=topic,
                    trigger_reason=_review_reason(module_name, should_distinguish, judge),
                    review_type="derive" if module_name == "derivation_coach" else "distinguish" if should_distinguish else "explain",
                    scheduled_time=scheduled,
                    success_criteria="Learner can restate the point and its boundary without AI help.",
                ).model_dump()
            )

        knowledge_positions = []
        if should_position:
            knowledge_positions.append(
                KnowledgePositionUpdate(
                    concept=topic,
                    layer="no_ai_internalization",
                    reason="No-AI or heavy learner-state evidence requires tracking internalization level.",
                    target_level="A3",
                    current_level="A1",
                    review_needed=True,
                ).model_dump()
            )

        derivation_updates = []
        if should_derivation:
            derivation_updates.append(
                DerivationTrustUpdate(
                    result_or_tool=topic,
                    assumptions=["Learner is working on a derivation or derivation trust gap."],
                    key_steps=["List assumptions.", "Reconstruct key steps.", "Mark steps that still require hints."],
                    done_by_user=[],
                    hinted_by_ai=["Initial derivation scaffold was provided by AI."],
                    untrusted_steps=["No independent reconstruction has been recorded yet."],
                    failure_conditions=["Learner cannot reproduce the derivation without prompts."],
                    no_ai_reconstruction_status="not_started",
                    next_rederive_time=scheduled,
                ).model_dump()
            )

        user_updates = {
            "claims": len(claims),
            "distinctions": len(distinctions),
            "temporal_traces": 1,
            "review_triggers": len(review_triggers),
            "knowledge_positions": len(knowledge_positions),
            "derivation_trust_records": len(derivation_updates),
        }
        return StateWriterOutput.model_validate(
            {
                "new_claims": claims,
                "updated_claims": [],
                "new_distinctions": distinctions,
                "new_temporal_trace": NewTemporalTrace(
                    event_type="chat",
                    user_question=message,
                    system_response_summary=answer.answer[:240],
                    state_change_summary=f"Recorded temporal trace plus {sum(count for key, count in user_updates.items() if key != 'temporal_traces')} durable learner-state updates.",
                    next_step=answer.suggested_next_action,
                ).model_dump(),
                "knowledge_position_updates": knowledge_positions,
                "derivation_trust_updates": derivation_updates,
                "review_triggers": review_triggers,
                "next_recommended_action": answer.suggested_next_action,
                "source_metadata": source_metadata,
                "user_originated_updates": user_updates,
                "ai_only_observations": {
                    "learning_state": judge.learning_state,
                    "knowledge_layer": judge.knowledge_layer,
                    "record_intensity": judge.record_intensity,
                    "module": module_name,
                },
                "discarded_ephemeral_judgments": {
                    "context_pack": "runtime_only",
                    "state_judge_label": "not_persisted_as_learning_memory",
                    "module_router_reason": "not_persisted_as_learning_memory",
                },
            }
        )


def _source_type_for_message(message: str) -> str:
    if _is_question(message):
        return "user_question"
    if any(marker in message for marker in ("我认为", "我觉得", "I think", "i think", "其实", "不是", "修正")):
        return "user_explicit"
    return "user_explicit"


def _evidence_text(message: str) -> str:
    return " ".join(message.strip().split())[:240]


def _is_question(message: str) -> bool:
    lowered = message.lower()
    return "?" in message or "？" in message or any(marker in message for marker in ("什么", "为什么", "吗", "是否", "是不是")) or lowered.startswith(("what", "why", "how", "is ", "are "))


def _should_write_claim(message: str) -> bool:
    if _is_low_content(message) or _is_operational(message):
        return False
    lowered = message.lower()
    conceptual_markers = (
        "what",
        "why",
        "how",
        "explain",
        "derive",
        "hypothesis",
        "i think",
        "claim",
    )
    chinese_markers = ("什么", "为什么", "是否", "是不是", "一定", "我认为", "我觉得", "推导", "解释", "区别", "误区", "修正")
    return _is_question(message) or any(marker in lowered for marker in conceptual_markers) or any(marker in message for marker in chinese_markers)


def _has_boundary_confusion(message: str, pack: ContextPackBuilderOutput, judge: StateJudgeOutput, module_name: str) -> bool:
    if _is_low_content(message) or _is_operational(message):
        return False
    lowered = message.lower()
    boundary_markers = ("区别", "是不是", "是否等同", "一定是", "等同", "和", " vs ", "compare", "difference", "same as")
    boundary_modules = {"example_comparison", "flawed_interpretation_critic", "review_point_runner", "no_ai_reconstruction_tester"}
    return (
        any(marker in message for marker in boundary_markers)
        or any(marker in lowered for marker in ("compare", "difference", "same as", " vs "))
        or bool(pack.known_confusions)
        or module_name in boundary_modules
        or "concept-boundary" in judge.risk_flags
    )


def _should_write_review_trigger(message: str, judge: StateJudgeOutput, module_name: str, distinction_created: bool) -> bool:
    if _is_low_content(message) or _is_operational(message):
        return False
    if distinction_created:
        return True
    if module_name in {"review_point_runner", "no_ai_reconstruction_tester"}:
        return True
    if module_name == "derivation_coach":
        return True
    if judge.knowledge_layer == "no_ai_internalization" and judge.record_intensity in {"medium", "heavy"}:
        return True
    return judge.record_intensity in {"medium", "heavy"} and _is_question(message)


def _should_write_knowledge_position(message: str, judge: StateJudgeOutput, module_name: str) -> bool:
    if module_name == "no_ai_reconstruction_tester":
        return True
    if any(marker in message for marker in ("内化", "不用 AI", "无 AI", "是否必须记住", "能否外包")):
        return True
    return judge.knowledge_layer == "no_ai_internalization" and judge.record_intensity == "heavy"


def _should_write_derivation_trust(message: str, judge: StateJudgeOutput, module_name: str) -> bool:
    lowered = message.lower()
    if module_name == "derivation_coach":
        return True
    if any(marker in message for marker in ("推导", "证明", "不信", "不放心")):
        return True
    if any(marker in lowered for marker in ("derive", "derivation", "prove", "trust")):
        return True
    return judge.record_intensity == "heavy" and judge.learning_state == "ready_for_derivation"


def _select_reference_chunks(repository: Any, references: list[dict[str, Any]], request: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for reference in references:
        for chunk in repository.list_reference_chunks(reference["id"]):
            candidates.append(
                {
                    "reference_id": reference["id"],
                    "title": reference.get("title", ""),
                    "reliability_level": reference.get("reliability_level", "uncertain"),
                    "scope": reference.get("scope", ""),
                    "section_title": chunk.get("section_title"),
                    "page_number": chunk.get("page_number"),
                    "chunk_text": str(chunk.get("chunk_text", ""))[:1200],
                }
            )
    ranked = rank_records(candidates, request, "reference_chunk", 6)
    total = 0
    selected: list[dict[str, Any]] = []
    for chunk in ranked:
        text = chunk.get("chunk_text", "")
        if total + len(text) > 5000:
            remaining = max(0, 5000 - total)
            if remaining <= 80:
                break
            chunk = {**chunk, "chunk_text": text[:remaining]}
            text = chunk["chunk_text"]
        selected.append(chunk)
        total += len(text)
    return selected


def _format_reference_context(chunks: list[dict[str, Any]], titles: list[str]) -> str:
    if not chunks:
        return "; ".join(titles) or "No selected references."
    sections: list[str] = []
    for chunk in chunks:
        sections.append(
            "\n".join(
                [
                    f"Reference: {chunk.get('title') or chunk.get('reference_id')}",
                    f"Reliability: {chunk.get('reliability_level', 'uncertain')}",
                    f"Scope: {chunk.get('scope', '')}",
                    f"Section: {chunk.get('section_title') or 'unknown'}",
                    f"Page: {chunk.get('page_number') if chunk.get('page_number') is not None else 'n/a'}",
                    "Excerpt:",
                    str(chunk.get("chunk_text", "")),
                ]
            )
        )
    return "\n\n".join(sections)


def _review_reason(module_name: str, distinction_created: bool, judge: StateJudgeOutput) -> str:
    if distinction_created:
        return "User-originated boundary confusion should be checked later."
    if module_name == "no_ai_reconstruction_tester":
        return "No-AI reconstruction needs a follow-up verification point."
    if module_name == "derivation_coach":
        return "Derivation trust is not established until the learner reconstructs key steps."
    if judge.learning_state == "needs_review":
        return "A pending review condition was detected."
    return "The turn left an open learner-side question."


def _split_boundary_concepts(message: str, topic: str) -> tuple[str, str]:
    for separator in ("和", "与", " vs ", " VS ", " versus "):
        if separator in message:
            left, right = message.split(separator, 1)
            left = left.strip(" ，,。?？")
            right = right.strip(" ，,。?？")
            return (left[:80] or topic, right[:80] or "nearby concept")
    return topic, "nearby concept or hidden assumption"


def _is_low_content(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"", "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "你好", "谢谢", "好的", "嗯", "好"}


def _is_operational(message: str) -> bool:
    normalized = message.strip().lower()
    operational_markers = (
        "简洁一点",
        "短一点",
        "长一点",
        "换中文",
        "用英文",
        "继续",
        "重新回答",
        "格式",
        "settings",
        "setting",
        "ui",
        "界面",
    )
    return any(marker in normalized for marker in operational_markers)

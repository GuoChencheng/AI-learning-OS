from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ailearn.agents.contracts import AnswerComposerOutput, ContextPackBuilderOutput, StateJudgeOutput, StateWriterOutput
from ailearn.agents.deterministic import AnswerComposerAgent, StateWriterAgent
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier


class ModelBackedAnswerComposerAgent:
    def __init__(self, model_gateway: ModelGateway) -> None:
        self.model_gateway = model_gateway
        self.fallback_agent = AnswerComposerAgent()

    def run(
        self,
        module_name: str,
        pack: ContextPackBuilderOutput,
        judge: StateJudgeOutput,
        active_unit: dict[str, Any] | None = None,
        project_settings: dict[str, Any] | None = None,
        system_settings: dict[str, Any] | None = None,
    ) -> AnswerComposerOutput:
        fallback = self.fallback_agent.run(module_name, pack, judge)
        prompt = _answer_prompt(module_name, pack, judge, active_unit, project_settings, system_settings)
        try:
            return self.model_gateway.complete_structured(prompt, AnswerComposerOutput, tier=ModelTier.STRONG, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            return fallback


class ModelBackedStateWriterAgent:
    def __init__(self, model_gateway: ModelGateway) -> None:
        self.model_gateway = model_gateway
        self.fallback_agent = StateWriterAgent()

    def run(
        self,
        project_id: str,
        message: str,
        answer: AnswerComposerOutput,
        pack: ContextPackBuilderOutput,
        judge: StateJudgeOutput,
        module_name: str,
        source_message_id: str | None,
        active_unit: dict[str, Any] | None = None,
    ) -> StateWriterOutput:
        fallback = self.fallback_agent.run(project_id, message, answer, pack, judge, module_name, source_message_id)
        if _is_low_content(message) or _is_operational(message):
            return fallback
        prompt = _state_writer_prompt(message, answer, pack, judge, module_name, active_unit, fallback)
        try:
            proposed = self.model_gateway.complete_structured(prompt, StateWriterOutput, tier=ModelTier.MEDIUM, fallback=fallback)
        except (ModelGatewayError, RuntimeError, ValueError, ValidationError):
            return fallback
        return _sanitize_state_writer_output(proposed, fallback, message, module_name)


def _answer_prompt(
    module_name: str,
    pack: ContextPackBuilderOutput,
    judge: StateJudgeOutput,
    active_unit: dict[str, Any] | None,
    project_settings: dict[str, Any] | None,
    system_settings: dict[str, Any] | None,
) -> str:
    return f"""
You are AI Learn OS, an AI-assisted learning operating system.

Return ONLY JSON matching this schema:
{{
  "answer": "string",
  "exercise": null | "string",
  "follow_up_question": null | "string",
  "suggested_next_action": "string"
}}

Teaching module: {module_name}
AI permission boundary: {pack.ai_permission_boundary}
Learning state: {judge.learning_state}
Knowledge layer: {judge.knowledge_layer}
Record intensity: {judge.record_intensity}
Active learning unit: {active_unit or {}}
Project settings: {project_settings or {}}
System settings: {system_settings or {}}

User request:
{pack.current_request}

Goal context:
{pack.goal_context}

Reference context. Prefer these excerpts as evidence when relevant:
{pack.reference_context}

Learning-state context:
{pack.learning_state_context}

Known confusions:
{pack.known_confusions}

Constraints:
- Teach, do not merely answer.
- Respect the selected teaching module.
- Do not claim the learner has understood something merely because AI explained it.
- Distinguish fact, inference, analogy, and learning strategy when relevant.
- Keep the response in the user's/project language when possible.
- If references are provided, use them as preferred evidence, but do not invent citations.
- Do not include chain-of-thought or hidden reasoning.
""".strip()


def _state_writer_prompt(
    message: str,
    answer: AnswerComposerOutput,
    pack: ContextPackBuilderOutput,
    judge: StateJudgeOutput,
    module_name: str,
    active_unit: dict[str, Any] | None,
    fallback: StateWriterOutput,
) -> str:
    return f"""
You are the structured State Writer for AI Learn OS.

Return ONLY JSON matching StateWriterOutput. Use the fallback shape as a guide:
{fallback.model_dump_json()}

User message:
{message}

Assistant answer:
{answer.answer}

Module: {module_name}
Active learning unit: {active_unit or {}}
Context pack:
{pack.model_dump_json()}
State judge:
{judge.model_dump_json()}

Rules:
- Do not summarize the assistant answer as learner understanding.
- Only write durable records grounded in the user's message, answer attempt, confusion, correction, derivation attempt, or no-AI test result.
- AI-only observations must remain in ai_only_observations or discarded_ephemeral_judgments.
- Greetings and operational messages create only a temporal trace.
- Ordinary explanation should not create KnowledgePosition or DerivationTrust.
- KnowledgePosition only for no-AI or explicit internalization evidence.
- DerivationTrust only for derivation attempts or trust gaps.
- ReviewTrigger only when there is a clear follow-up learning need.
""".strip()


def _sanitize_state_writer_output(output: StateWriterOutput, fallback: StateWriterOutput, message: str, module_name: str) -> StateWriterOutput:
    data = output.model_dump(mode="json")
    data["source_metadata"] = fallback.source_metadata.model_dump(mode="json")
    if _is_low_content(message) or _is_operational(message):
        return fallback
    if module_name != "no_ai_reconstruction_tester" and not any(marker in message for marker in ("内化", "不用 AI", "无 AI", "是否必须记住", "能否外包")):
        data["knowledge_position_updates"] = fallback.model_dump(mode="json")["knowledge_position_updates"]
    if module_name != "derivation_coach" and not _mentions_derivation(message):
        data["derivation_trust_updates"] = fallback.model_dump(mode="json")["derivation_trust_updates"]
    if not data.get("new_temporal_trace"):
        data["new_temporal_trace"] = fallback.new_temporal_trace.model_dump(mode="json")
    data["discarded_ephemeral_judgments"] = {
        **data.get("discarded_ephemeral_judgments", {}),
        "state_writer_model_output": "sanitized_before_persistence",
    }
    return StateWriterOutput.model_validate(data)


def _mentions_derivation(message: str) -> bool:
    lowered = message.lower()
    return any(marker in message for marker in ("推导", "证明", "不信", "不放心")) or any(marker in lowered for marker in ("derive", "derivation", "prove", "trust"))


def _is_low_content(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"", "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "你好", "谢谢", "好的", "嗯", "好"}


def _is_operational(message: str) -> bool:
    normalized = message.strip().lower()
    return any(marker in normalized for marker in ("简洁一点", "短一点", "长一点", "换中文", "用英文", "继续", "重新回答", "格式", "settings", "setting", "ui", "界面"))

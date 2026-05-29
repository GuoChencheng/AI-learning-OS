from __future__ import annotations

import pytest
from pydantic import ValidationError

from ailearn.agents.contracts import (
    AnswerComposerOutput,
    ContextPackBuilderOutput,
    RequestIntakeOutput,
    StateWriterOutput,
)
from ailearn.modules.router import ModuleRouter, ModuleRoutingInput


def test_agent_contracts_validate_strict_enums() -> None:
    intake = RequestIntakeOutput.model_validate(
        {
            "intent": "ask_concept",
            "topic": "critical phenomena",
            "urgency": "medium",
            "needs_reference": True,
            "needs_state_read": True,
            "user_selected_mode": "explain",
        }
    )

    assert intake.intent == "ask_concept"

    with pytest.raises(ValidationError):
        RequestIntakeOutput.model_validate(
            {
                "intent": "freeform_chat",
                "topic": "critical phenomena",
                "urgency": "medium",
                "needs_reference": True,
                "needs_state_read": True,
                "user_selected_mode": "explain",
            }
        )


def test_context_pack_and_state_writer_contracts_match_api_shape() -> None:
    pack = ContextPackBuilderOutput.model_validate(
        {
            "current_request": "二阶相变处一定是 CFT 吗？",
            "goal_context": "Understand phase transitions for field theory.",
            "reference_context": "No selected references.",
            "learning_state_context": "Learner is distinguishing scale invariance and conformal invariance.",
            "known_confusions": ["scale invariance vs conformal invariance"],
            "must_respect_constraints": ["Do not mark learned without evidence."],
            "suggested_learning_action": "compare",
            "ai_permission_boundary": "direct_answer",
        }
    )
    answer = AnswerComposerOutput(
        answer="Not always; extra assumptions matter.",
        exercise=None,
        follow_up_question=None,
        suggested_next_action="Run a distinction check.",
    )
    writer = StateWriterOutput.model_validate(
        {
            "new_claims": [
                {
                    "original_statement": pack.current_request,
                    "normalized_statement": "Second-order phase transitions are not automatically CFTs.",
                    "related_concept": "critical phenomena",
                    "epistemic_status": "standard_interpretation",
                    "confidence": 0.55,
                    "correction": answer.answer,
                }
            ],
            "updated_claims": [],
            "new_distinctions": [
                {
                    "concept_a": "scale invariance",
                    "concept_b": "conformal invariance",
                    "boundary": "Conformal invariance is stronger and may require assumptions.",
                    "common_confusion": "Treating criticality as automatically conformal.",
                    "example": "Long-range systems can break common short-range assumptions.",
                    "test_question": "Name one assumption needed for scale to imply conformal.",
                }
            ],
            "new_temporal_trace": {
                "event_type": "chat",
                "user_question": pack.current_request,
                "system_response_summary": "Explained non-equivalence and assumptions.",
                "state_change_summary": "Added claim and distinction.",
                "next_step": answer.suggested_next_action,
            },
            "knowledge_position_updates": [],
            "derivation_trust_updates": [],
            "review_triggers": [
                {
                    "target": "scale invariance vs conformal invariance",
                    "trigger_reason": "New adjacent-concept distinction.",
                    "review_type": "distinguish",
                    "scheduled_time": "2030-01-01T00:00:00Z",
                    "success_criteria": "Explain the boundary without AI.",
                }
            ],
            "next_recommended_action": answer.suggested_next_action,
            "source_metadata": {
                "source_type": "user_question",
                "source_message_id": "msg_test",
                "evidence_text": pack.current_request,
            },
            "user_originated_updates": {"claims": 1, "distinctions": 1, "review_triggers": 1},
            "ai_only_observations": {"learning_state": "confused"},
            "discarded_ephemeral_judgments": {"context_pack": "runtime_only"},
        }
    )

    assert writer.new_claims[0].related_concept == "critical phenomena"
    assert writer.new_distinctions[0].concept_a == "scale invariance"
    assert writer.review_triggers[0].review_type == "distinguish"
    assert writer.source_metadata.source_type == "user_question"
    assert writer.discarded_ephemeral_judgments["context_pack"] == "runtime_only"


def test_module_router_priority_user_button_project_setting_state_default() -> None:
    router = ModuleRouter()

    assert (
        router.route(
            ModuleRoutingInput(
                button_action="derive",
                selected_mode="auto",
                project_default_mode="exercise",
                state_recommendation="review",
            )
        ).module
        == "derivation_coach"
    )
    assert (
        router.route(
            ModuleRoutingInput(
                button_action=None,
                selected_mode="auto",
                project_default_mode="exercise",
                state_recommendation="review",
            )
        ).module
        == "exercise_generator"
    )
    assert (
        router.route(
            ModuleRoutingInput(
                button_action=None,
                selected_mode="auto",
                project_default_mode=None,
                state_recommendation="review",
            )
        ).module
        == "review_point_runner"
    )
    assert (
        router.route(
            ModuleRoutingInput(
                button_action=None,
                selected_mode="auto",
                project_default_mode=None,
                state_recommendation=None,
            )
        ).module
        == "concept_explainer"
    )

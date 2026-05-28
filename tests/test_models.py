from datetime import datetime

import pytest
from pydantic import ValidationError

from ailearn.ids import new_id
from ailearn.models import (
    ClaimRecord,
    DerivationRecord,
    Goal,
    ReferenceRecord,
    PositionDecision,
    SessionFootprint,
    TestRecord,
)


def test_goal_defaults_include_active_state_and_timestamps():
    goal = Goal(
        id="goal_test",
        title="Quantum mechanics",
        main_goal="Understand operators",
        stage_goal="Work through perturbation theory",
        transfer_goal="Apply ideas in new systems",
        external_goal="Prepare for research",
        priority_topics=["density_matrix"],
    )

    assert goal.active is True
    assert isinstance(goal.created_at, datetime)
    assert isinstance(goal.updated_at, datetime)


def test_position_decision_rejects_invalid_position():
    with pytest.raises(ValidationError):
        PositionDecision(
            id="pos_test",
            goal_id="goal_test",
            knowledge_point="density_matrix",
            position="knowledge_graph_node",
            tool_role="core_tool",
            reason="Needed for mixed states",
            confidence="high",
            epistemic_status="learning_strategy",
            revisit_when=["after decoherence"],
            record_strength="medium",
        )


def test_position_decision_tracks_record_intensity_and_internalization_level():
    position = PositionDecision(
        id="pos_internalization",
        goal_id="goal_test",
        knowledge_point="Hilbert space",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core disciplinary language",
        confidence="high",
        epistemic_status="learning_strategy",
        revisit_when=["before spectral theorem"],
        record_strength="heavy",
        record_intensity="heavy",
        internalization_level="A1",
    )

    assert position.record_intensity == "heavy"
    assert position.internalization_level == "A1"


def test_claim_record_requires_known_epistemic_status():
    claim = ClaimRecord(
        id="claim_test",
        goal_id="goal_test",
        text="Perturbation theory is a low-order expansion.",
        context="Physics study",
        type="interpretation",
        status="unverified",
        epistemic_status="heuristic",
        strict_part="Series expansion around solvable system",
        caveat="Effective theory has separate assumptions",
        counterexample_or_boundary="Strong coupling",
        next_action="Verify with examples",
        record_intensity="medium",
    )

    assert claim.epistemic_status == "heuristic"
    assert claim.record_intensity == "medium"


def test_derivation_record_tracks_user_and_ai_steps_separately():
    derivation = DerivationRecord(
        id="der_test",
        goal_id="goal_test",
        topic="nondegenerate_perturbation_theory",
        importance="core_tool",
        status="partial",
        result_to_trust="First-order energy correction",
        user_derived_steps=["Set up eigenvalue expansion"],
        ai_hinted_steps=["Projection step"],
        not_yet_trusted=["Second-order correction"],
        next_action="Re-derive without hints",
        record_intensity="heavy",
    )

    assert derivation.user_derived_steps == ["Set up eigenvalue expansion"]
    assert derivation.ai_hinted_steps == ["Projection step"]
    assert derivation.record_intensity == "heavy"


def test_reference_record_captures_source_index_not_world_knowledge():
    reference = ReferenceRecord(
        id="ref_test",
        goal_id="goal_test",
        title="Quantum Computation and Quantum Information",
        authors_or_source="Nielsen and Chuang",
        reference_type="textbook",
        path_or_url="https://example.com/nc",
        topics=["density_matrix", "quantum_channels"],
        relevance_to_goal="Durable source for formal language.",
        usage_stage="core_learning",
        reading_status="skimmed",
        notes="Use as source index, not copied encyclopedia notes.",
    )

    assert reference.reference_type == "textbook"
    assert reference.usage_stage == "core_learning"
    assert reference.reading_status == "skimmed"


def test_test_record_tracks_internalization_target_and_prompt():
    record = TestRecord(
        id="test_test",
        goal_id="goal_test",
        topic="perturbation_theory",
        position_id="pos_test",
        test_type="derivation_reconstruction",
        status="planned",
        internalization_target="A3",
        prompt="Reconstruct the derivation without AI.",
    )

    assert record.internalization_target == "A3"
    assert record.status == "planned"


def test_session_footprint_frontmatter_model():
    session = SessionFootprint(
        id="session_test",
        goal_id="goal_test",
        topic="perturbation_theory",
        mode="derivation",
        learning_state="formula_without_trust",
        methods_used=["derivation_trust"],
        references_used=["ref_test"],
        provisional_understanding="I can use the formula but do not trust the derivation.",
        test_mode_triggered=True,
        references_added=["ref_new"],
    )

    assert session.topic == "perturbation_theory"
    assert session.mode == "derivation"
    assert session.learning_state == "formula_without_trust"
    assert session.test_mode_triggered is True


def test_new_id_uses_prefix_and_unique_suffix():
    first = new_id("goal")
    second = new_id("goal")

    assert first.startswith("goal_")
    assert second.startswith("goal_")
    assert first != second

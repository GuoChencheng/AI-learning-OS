from pathlib import Path

from ailearn.models import (
    ClaimRecord,
    DerivationRecord,
    Goal,
    PositionDecision,
    ReferenceRecord,
    SessionFootprint,
    TestRecord,
)
from ailearn.review import generate_weekly_review
from ailearn.storage import init_project, save_session, save_yaml_model


def test_generate_weekly_review_summarizes_learning_state(tmp_path: Path):
    init_project(tmp_path)
    goal = Goal(
        id="goal_review",
        title="Physics",
        main_goal="Learn perturbation theory",
        stage_goal="First-order results",
        transfer_goal="Use in new models",
        external_goal="Research prep",
        priority_topics=["perturbation_theory"],
    )
    claim = ClaimRecord(
        id="claim_review",
        goal_id=goal.id,
        text="Perturbation theory resembles low-order effective theory.",
        context="Session comparison",
        type="interpretation",
        status="unverified",
        epistemic_status="inference",
        strict_part="",
        caveat="",
        counterexample_or_boundary="",
        next_action="Ask AI to verify boundaries",
    )
    derivation = DerivationRecord(
        id="der_review",
        goal_id=goal.id,
        topic="nondegenerate_perturbation_theory",
        importance="core_tool",
        status="needs_rederive",
        result_to_trust="Energy correction",
        user_derived_steps=[],
        ai_hinted_steps=["Projection"],
        not_yet_trusted=["Normalization"],
        next_action="Redo unaided",
    )
    position = PositionDecision(
        id="pos_review",
        goal_id=goal.id,
        knowledge_point="density_matrix",
        position="B_knowledge_positioning",
        tool_role="core_tool",
        reason="Needed to orient mixed-state problems",
        confidence="medium",
        epistemic_status="learning_strategy",
        revisit_when=["after decoherence"],
        record_strength="medium",
        record_intensity="medium",
        internalization_level="A0",
    )
    reference = ReferenceRecord(
        id="ref_review",
        goal_id=goal.id,
        title="Quantum lecture notes",
        authors_or_source="Course",
        reference_type="lecture_note",
        path_or_url="notes.md",
        topics=["perturbation_theory"],
        relevance_to_goal="Initial source map",
        usage_stage="initial_map",
        reading_status="skimmed",
        notes="",
    )
    test = TestRecord(
        id="test_review",
        goal_id=goal.id,
        topic="density_matrix",
        position_id=position.id,
        test_type="no_ai_explanation",
        status="planned",
        internalization_target="A1",
        prompt="Explain without AI.",
    )
    session = SessionFootprint(
        id="session_review",
        goal_id=goal.id,
        topic="perturbation_theory",
        mode="derivation",
        learning_state="formula_without_trust",
        references_used=[reference.id],
    )

    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    save_yaml_model(tmp_path / "data" / "derivations" / f"{derivation.id}.yaml", derivation)
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)
    save_yaml_model(tmp_path / "data" / "references" / f"{reference.id}.yaml", reference)
    save_yaml_model(tmp_path / "data" / "tests" / f"{test.id}.yaml", test)
    save_session(
        tmp_path / "data" / "sessions" / f"{session.id}.md",
        session,
        {"Started with": "Question", "Next actions": "Redo derivation"},
    )

    review_path = generate_weekly_review(tmp_path)
    text = review_path.read_text(encoding="utf-8")

    assert "perturbation_theory" in text
    assert claim.text in text
    assert "nondegenerate_perturbation_theory" in text
    assert "density_matrix" in text
    assert "after decoherence" in text
    assert "Suggested Socratic Drill Topics" in text
    assert "Quantum lecture notes" in text
    assert "Topics Ready For Test Mode" in text
    assert "A-Level Internalization Progress" in text
    assert "formula_without_trust" in text
    assert "Next Week Top 3 Actions" in text

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
from ailearn.status import project_status, render_status, suggest_next_actions
from ailearn.storage import init_project, save_session, save_yaml_model


def seed_status_project(tmp_path: Path) -> None:
    init_project(tmp_path)
    goal = Goal(
        id="goal_status",
        title="Topological order",
        main_goal="Read papers",
        stage_goal="Density matrices and perturbation",
        transfer_goal="Apply to model papers",
        external_goal="Research prep",
        priority_topics=["density_matrix"],
    )
    reference = ReferenceRecord(
        id="ref_status",
        goal_id=goal.id,
        title="Lecture notes",
        authors_or_source="Course",
        reference_type="lecture_note",
        path_or_url="notes.pdf",
        topics=["density_matrix"],
        relevance_to_goal="Initial map",
        usage_stage="initial_map",
        reading_status="skimmed",
        notes="",
    )
    claim = ClaimRecord(
        id="claim_status",
        goal_id=goal.id,
        text="Perturbation theory is a low-order effective theory.",
        context="session",
        type="interpretation",
        status="unverified",
        epistemic_status="inference",
        record_intensity="heavy",
    )
    derivation = DerivationRecord(
        id="der_status",
        goal_id=goal.id,
        topic="nondegenerate_perturbation_theory",
        importance="core_tool",
        status="needs_rederive",
        result_to_trust="Second-order energy correction",
        record_intensity="heavy",
    )
    position = PositionDecision(
        id="pos_status",
        goal_id=goal.id,
        knowledge_point="density_matrix",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core language",
        confidence="medium",
        epistemic_status="learning_strategy",
        revisit_when=["after decoherence"],
        record_intensity="heavy",
        internalization_level="A0",
    )
    test = TestRecord(
        id="test_status",
        goal_id=goal.id,
        topic="perturbation_theory",
        test_type="mixed",
        status="planned",
        internalization_target="A3",
        prompt="Test yourself.",
    )
    session = SessionFootprint(
        id="session_status",
        goal_id=goal.id,
        topic="perturbation_theory",
        mode="derivation",
        learning_state="formula_without_trust",
    )
    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "references" / f"{reference.id}.yaml", reference)
    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    save_yaml_model(tmp_path / "data" / "derivations" / f"{derivation.id}.yaml", derivation)
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)
    save_yaml_model(tmp_path / "data" / "tests" / f"{test.id}.yaml", test)
    save_session(tmp_path / "data" / "sessions" / f"{session.id}.md", session)


def test_project_status_summarizes_learning_state(tmp_path: Path):
    seed_status_project(tmp_path)

    summary = project_status(tmp_path)
    text = render_status(summary)

    assert summary.active_goal_title == "Topological order"
    assert summary.references_count == 1
    assert summary.unverified_claims == 1
    assert summary.derivations_needing_trust == 1
    assert summary.a_level_counts["A0"] == 1
    assert summary.tests_attention == 1
    assert "Recent sessions: perturbation_theory" in text


def test_next_actions_prioritize_heavy_unverified_claims(tmp_path: Path):
    seed_status_project(tmp_path)

    actions = suggest_next_actions(tmp_path)

    assert actions[0].startswith("Verify high/medium/heavy claim")
    assert any("derivation trust" in action for action in actions)
    assert len(actions) <= 5

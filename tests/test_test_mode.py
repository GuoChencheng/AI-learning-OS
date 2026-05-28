from pathlib import Path

from ailearn.models import ClaimRecord, DerivationRecord, Goal, PositionDecision, SessionFootprint, TestRecord
from ailearn.storage import init_project, save_session, save_yaml_model
from ailearn.test_mode import suggest_tests, test_record_prompt


def test_test_record_prompt_uses_record_context():
    goal = Goal(
        id="goal_testmode",
        title="QM",
        main_goal="Learn perturbation",
        stage_goal="Derive",
        transfer_goal="Apply",
        external_goal="Exam",
        priority_topics=[],
    )
    record = TestRecord(
        id="test_prompt",
        goal_id=goal.id,
        topic="perturbation_theory",
        test_type="mixed",
        status="planned",
        internalization_target="A3",
        prompt="",
    )

    prompt = test_record_prompt(goal, record)

    assert "perturbation_theory" in prompt
    assert "mixed" in prompt
    assert "A3" in prompt
    assert "no-AI" in prompt


def test_suggest_tests_finds_a_items_heavy_derivations_and_repeated_sessions(tmp_path: Path):
    init_project(tmp_path)
    goal = Goal(
        id="goal_suggest_tests",
        title="QM",
        main_goal="Learn perturbation",
        stage_goal="Derive",
        transfer_goal="Apply",
        external_goal="Exam",
        priority_topics=[],
    )
    position = PositionDecision(
        id="pos_suggest_tests",
        goal_id=goal.id,
        knowledge_point="density_matrix",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core language",
        confidence="high",
        epistemic_status="learning_strategy",
        record_intensity="heavy",
        internalization_level="A0",
    )
    derivation = DerivationRecord(
        id="der_suggest_tests",
        goal_id=goal.id,
        topic="nondegenerate_perturbation_theory",
        importance="core_tool",
        status="partial",
        result_to_trust="Second-order correction",
        record_intensity="heavy",
    )
    claim = ClaimRecord(
        id="claim_suggest_tests",
        goal_id=goal.id,
        text="Perturbation theory is controlled by small parameters.",
        context="",
        type="interpretation",
        status="verified",
        epistemic_status="standard_interpretation",
        record_intensity="medium",
    )
    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)
    save_yaml_model(tmp_path / "data" / "derivations" / f"{derivation.id}.yaml", derivation)
    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    for index in range(2):
        session = SessionFootprint(
            id=f"session_repeat_{index}",
            goal_id=goal.id,
            topic="perturbation_theory",
            mode="study",
        )
        save_session(tmp_path / "data" / "sessions" / f"{session.id}.md", session)

    suggestions = suggest_tests(tmp_path)

    assert any("density_matrix" in suggestion for suggestion in suggestions)
    assert any("nondegenerate_perturbation_theory" in suggestion for suggestion in suggestions)
    assert any("perturbation_theory" in suggestion for suggestion in suggestions)

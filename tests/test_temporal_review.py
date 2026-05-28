from datetime import timedelta
from pathlib import Path

from ailearn.models import (
    ClaimRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
)
from ailearn.review import due_review_items, generate_weekly_review
from ailearn.status import project_status, render_status, suggest_next_actions
from ailearn.storage import init_project, save_yaml_model
from ailearn.temporal import classify_temporal_state
from ailearn.ids import now_utc


def seed_temporal_project(tmp_path: Path) -> tuple[Goal, DistinctionRecord, MisconceptionRecord]:
    init_project(tmp_path)
    now = now_utc()
    goal = Goal(
        id="goal_temporal",
        title="QM temporal",
        main_goal="Read papers",
        stage_goal="Distinguish adjacent concepts",
        transfer_goal="Use distinctions while reading",
        external_goal="Research prep",
        priority_topics=["superposition", "entanglement"],
    )
    position = PositionDecision(
        id="pos_due",
        goal_id=goal.id,
        knowledge_point="density_matrix",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core language",
        confidence="medium",
        epistemic_status="learning_strategy",
        internalization_level="A1",
        next_review_at=now - timedelta(days=1),
    )
    claim = ClaimRecord(
        id="claim_stale",
        goal_id=goal.id,
        text="All superpositions are entangled.",
        context="session",
        type="hypothesis",
        status="unverified",
        epistemic_status="speculation",
        record_intensity="medium",
        first_seen_at=now - timedelta(days=30),
    )
    distinction = DistinctionRecord(
        id="dist_due",
        goal_id=goal.id,
        title="superposition vs entanglement",
        concepts=["superposition_state", "entangled_state"],
        confusion_statement="I cannot separate superposition from entanglement.",
        status="needs_test",
        internalization_target="A2",
        next_distinction_test_at=now - timedelta(days=1),
        confusion_count=2,
        next_action="Run distinction test.",
    )
    misconception = MisconceptionRecord(
        id="misc_recurring",
        goal_id=goal.id,
        statement="All superpositions are entangled.",
        why_wrong="Entanglement requires composite non-factorizable structure.",
        corrected_view="Some superpositions are single-system states.",
        related_topics=["superposition", "entanglement"],
        severity="important",
        status="recurring",
        recurrence_count=2,
        next_action="Test with Bell state and single qubit examples.",
    )
    for directory, record in [
        ("goals", goal),
        ("positioning", position),
        ("claims", claim),
        ("distinctions", distinction),
        ("misconceptions", misconception),
    ]:
        save_yaml_model(tmp_path / "data" / directory / f"{record.id}.yaml", record)
    return goal, distinction, misconception


def test_temporal_state_classifier_marks_due_overdue_and_recent():
    now = now_utc()

    assert classify_temporal_state(first_seen_at=now - timedelta(hours=2), now=now) == "new_or_provisional"
    assert classify_temporal_state(last_reviewed_at=now - timedelta(days=9), review_interval_days=7, now=now) == "review_due"
    assert classify_temporal_state(next_review_at=now - timedelta(days=2), now=now) == "overdue"
    assert classify_temporal_state(last_checked_at=now - timedelta(days=1), now=now) == "recently_verified"


def test_next_and_status_include_due_distinctions_and_recurring_misconceptions(tmp_path: Path):
    seed_temporal_project(tmp_path)

    status = project_status(tmp_path)
    actions = suggest_next_actions(tmp_path, limit=10)
    rendered = render_status(status)

    assert status.distinctions_attention == 1
    assert status.recurring_misconceptions == 1
    assert "Distinctions needing attention: 1" in rendered
    assert any("distinction test" in action.lower() for action in actions)
    assert any("recurring misconception" in action.lower() for action in actions)
    assert any("review due" in action.lower() for action in actions)


def test_weekly_review_and_due_review_include_temporal_items(tmp_path: Path):
    _, distinction, misconception = seed_temporal_project(tmp_path)

    due = due_review_items(tmp_path)
    review_path = generate_weekly_review(tmp_path)
    text = review_path.read_text(encoding="utf-8")

    assert any(distinction.id in item for item in due)
    assert any(misconception.id in item for item in due)
    assert "Distinctions Needing Tests" in text
    assert "Repeated Misconceptions" in text
    assert "Records With Due Reviews" in text
    assert "superposition vs entanglement" in text

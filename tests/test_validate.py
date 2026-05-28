from pathlib import Path

import yaml

from ailearn.models import ClaimRecord, Goal, PositionDecision, ReferenceRecord, TestRecord
from ailearn.events import LearningEvent, append_event
from ailearn.storage import init_project, save_yaml_model
from ailearn.validate import validate_project


def test_validate_project_reports_invalid_yaml_record(tmp_path: Path):
    init_project(tmp_path)
    broken = tmp_path / "data" / "claims" / "bad.yaml"
    broken.write_text(
        yaml.safe_dump(
            {
                "id": "bad",
                "goal_id": "missing_goal",
                "text": "Bad claim",
                "context": "",
                "type": "not_a_type",
                "status": "unverified",
                "epistemic_status": "inference",
            }
        ),
        encoding="utf-8",
    )

    report = validate_project(tmp_path)

    assert not report.ok
    assert any("bad.yaml" in error for error in report.errors)
    assert any("type" in error for error in report.errors)


def test_validate_project_reports_broken_goal_reference(tmp_path: Path):
    init_project(tmp_path)
    claim = ClaimRecord(
        id="claim_orphan",
        goal_id="missing_goal",
        text="An orphaned claim",
        context="",
        type="hypothesis",
        status="unverified",
        epistemic_status="speculation",
        strict_part="",
        caveat="",
        counterexample_or_boundary="",
        next_action="Create a goal",
    )

    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    report = validate_project(tmp_path)

    assert not report.ok
    assert any("broken goal_id" in error for error in report.errors)


def test_validate_project_checks_reference_and_test_goal_references(tmp_path: Path):
    init_project(tmp_path)
    reference = ReferenceRecord(
        id="ref_orphan",
        goal_id="missing_goal",
        title="Orphan source",
        authors_or_source="Nobody",
        reference_type="other",
        path_or_url="source.md",
        topics=[],
        relevance_to_goal="",
        usage_stage="optional",
        reading_status="unread",
        notes="",
    )
    test = TestRecord(
        id="test_orphan",
        goal_id="missing_goal",
        topic="density_matrix",
        test_type="mixed",
        status="planned",
        internalization_target="A1",
        prompt="",
    )

    save_yaml_model(tmp_path / "data" / "references" / f"{reference.id}.yaml", reference)
    save_yaml_model(tmp_path / "data" / "tests" / f"{test.id}.yaml", test)
    report = validate_project(tmp_path)

    assert not report.ok
    assert any("ref_orphan.yaml" in error for error in report.errors)
    assert any("test_orphan.yaml" in error for error in report.errors)


def test_validate_project_warns_when_b_or_c_has_a_level_internalization(tmp_path: Path):
    init_project(tmp_path)
    goal = Goal(
        id="goal_warn",
        title="Warn",
        main_goal="Learn",
        stage_goal="Stage",
        transfer_goal="Transfer",
        external_goal="Exam",
        priority_topics=[],
    )
    position = PositionDecision(
        id="pos_warn",
        goal_id=goal.id,
        knowledge_point="optional_topic",
        position="C_index_recall",
        tool_role="none",
        reason="Only an entry point",
        confidence="medium",
        epistemic_status="learning_strategy",
        internalization_level="A2",
    )

    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)
    report = validate_project(tmp_path)

    assert report.ok
    assert any("internalization_level" in warning for warning in report.warnings)


def test_validate_project_accepts_valid_goal_and_claim(tmp_path: Path):
    init_project(tmp_path)
    goal = Goal(
        id="goal_valid",
        title="Physics",
        main_goal="Learn",
        stage_goal="Practice",
        transfer_goal="Apply",
        external_goal="Exam",
        priority_topics=[],
    )
    claim = ClaimRecord(
        id="claim_valid",
        goal_id=goal.id,
        text="A valid claim",
        context="",
        type="hypothesis",
        status="unverified",
        epistemic_status="speculation",
        strict_part="",
        caveat="",
        counterexample_or_boundary="",
        next_action="Verify",
    )

    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    report = validate_project(tmp_path)

    assert report.ok


def test_validate_project_reports_malformed_event_jsonl(tmp_path: Path):
    init_project(tmp_path)
    events = tmp_path / "data" / "events" / "2026-05.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text('{"event_type": "record_created"}\nnot-json\n', encoding="utf-8")

    report = validate_project(tmp_path)

    assert not report.ok
    assert any("malformed event JSONL" in error for error in report.errors)


def test_validate_project_checks_event_enum_and_related_goal(tmp_path: Path):
    init_project(tmp_path)
    append_event(
        LearningEvent.new(
            event_type="record_created",
            target_type="claim",
            target_id="claim_event",
            goal_id="missing_goal",
            summary="Created orphan claim event.",
            source="system",
        ),
        root=tmp_path,
    )

    report = validate_project(tmp_path)

    assert not report.ok
    assert any("broken event goal_id" in error for error in report.errors)

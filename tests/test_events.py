from pathlib import Path

from ailearn.events import (
    LearningEvent,
    append_event,
    build_timeline,
    load_events,
    load_events_for_target,
    load_events_for_type,
    summarize_events_for_record,
)
from ailearn.storage import init_project


def test_append_and_load_event_jsonl_by_month_target_and_type(tmp_path: Path):
    init_project(tmp_path)

    event = append_event(
        LearningEvent.new(
            event_type="position_changed",
            target_type="positioning",
            target_id="pos_density",
            goal_id="goal_qm",
            summary="density_matrix moved from B to A0",
            before={"position": "B_knowledge_positioning"},
            after={"position": "A_no_ai_internalization", "internalization_level": "A0"},
            source="codex",
        ),
        root=tmp_path,
    )

    month = event.timestamp_utc.strftime("%Y-%m")
    assert (tmp_path / "data" / "events" / f"{month}.jsonl").is_file()
    assert load_events(month, root=tmp_path)[0].id == event.id
    assert load_events_for_target("pos_density", root=tmp_path)[0].event_type == "position_changed"
    assert load_events_for_type("position_changed", root=tmp_path)[0].target_id == "pos_density"


def test_event_timeline_and_summary_are_compact(tmp_path: Path):
    init_project(tmp_path)
    append_event(
        LearningEvent.new(
            event_type="confusion_recorded",
            target_type="distinction",
            target_id="dist_superposition_entanglement",
            summary="Learner confused superposition with entanglement.",
            source="user",
        ),
        root=tmp_path,
    )
    append_event(
        LearningEvent.new(
            event_type="delayed_retrieval_failed",
            target_type="distinction",
            target_id="dist_superposition_entanglement",
            summary="Failed delayed distinction test.",
            reason="Could not give a counterexample.",
            source="system",
        ),
        root=tmp_path,
    )

    timeline = build_timeline("dist_superposition_entanglement", root=tmp_path)
    summary = summarize_events_for_record("dist_superposition_entanglement", root=tmp_path)

    assert len(timeline) == 2
    assert "confusion_recorded" in timeline[0]
    assert "delayed_retrieval_failed" in summary
    assert "Could not give a counterexample" in summary


def test_event_local_timestamp_uses_default_project_timezone(tmp_path: Path):
    init_project(tmp_path)

    event = append_event(
        LearningEvent.new(
            event_type="record_created",
            target_type="claim",
            target_id="claim_time",
            summary="Created claim.",
            source="system",
        ),
        root=tmp_path,
    )

    assert event.timestamp_utc.tzinfo is not None
    assert event.timezone == "Asia/Shanghai"
    assert event.timestamp_local.tzinfo is not None

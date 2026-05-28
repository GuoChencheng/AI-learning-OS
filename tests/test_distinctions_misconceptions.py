from pathlib import Path

from ailearn.models import ConceptClusterRecord, DistinctionRecord, Goal, MisconceptionRecord
from ailearn.prompts import (
    distinction_prompt,
    distinction_test_prompt,
    misconception_correction_prompt,
    temporal_review_prompt,
)
from ailearn.storage import init_project, load_yaml_model, save_yaml_model


def test_distinction_record_schema_and_storage_round_trip(tmp_path: Path):
    init_project(tmp_path)
    record = DistinctionRecord(
        id="dist_superposition_entanglement",
        goal_id="goal_qm",
        title="superposition vs entanglement",
        concepts=["superposition_state", "entangled_state"],
        confusion_statement="I keep treating every superposition as entanglement.",
        status="needs_distinction",
        internalization_target="A2",
        record_intensity="medium",
        confusion_count=1,
        next_action="Generate a distinction test.",
    )

    save_yaml_model(tmp_path / "data" / "distinctions" / f"{record.id}.yaml", record)
    loaded = load_yaml_model(tmp_path / "data" / "distinctions" / f"{record.id}.yaml", DistinctionRecord)

    assert loaded.concepts == ["superposition_state", "entangled_state"]
    assert loaded.status == "needs_distinction"
    assert loaded.confusion_count == 1


def test_misconception_record_schema_supports_recurrence():
    record = MisconceptionRecord(
        id="misc_all_superpositions_entangled",
        goal_id="goal_qm",
        statement="All superpositions are entangled.",
        why_wrong="Entanglement requires a composite system and non-factorizable state.",
        corrected_view="Single-system superpositions need not be entangled.",
        related_topics=["superposition", "entanglement"],
        severity="important",
        status="recurring",
        recurrence_count=3,
        next_action="Run retrieval test with counterexamples.",
    )

    assert record.status == "recurring"
    assert record.recurrence_count == 3


def test_concept_cluster_record_is_lightweight_learning_state():
    record = ConceptClusterRecord(
        id="cluster_topological_order",
        goal_id="goal_qm",
        title="topological order language cluster",
        core_question="Which QM concepts repeatedly appear together in papers?",
        concepts=["density_matrix", "entanglement_entropy", "ground_state_degeneracy"],
        current_status="provisional",
        reason="These appear together in the current reading goal.",
        next_action="Use only as learning-state grouping.",
    )

    assert record.current_status == "provisional"
    assert "density_matrix" in record.concepts


def test_distinction_and_misconception_prompts_are_not_encyclopedia_prompts():
    goal = Goal(
        id="goal_qm",
        title="QM",
        main_goal="Read topological order papers",
        stage_goal="Clarify adjacent concepts",
        transfer_goal="Use distinctions in paper reading",
        external_goal="Research prep",
        priority_topics=["superposition", "entanglement"],
    )
    distinction = DistinctionRecord(
        id="dist_test",
        goal_id=goal.id,
        title="superposition vs entanglement",
        concepts=["superposition_state", "entangled_state"],
        confusion_statement="All superpositions feel entangled.",
        status="needs_distinction",
    )
    misconception = MisconceptionRecord(
        id="misc_test",
        goal_id=goal.id,
        statement="All superpositions are entangled.",
        why_wrong="",
        corrected_view="",
        related_topics=["superposition", "entanglement"],
        severity="important",
        status="active",
    )

    distinction_text = distinction_prompt(goal, distinction)
    test_text = distinction_test_prompt(goal, distinction)
    misconception_text = misconception_correction_prompt(goal, misconception)
    temporal_text = temporal_review_prompt(["2026-05-26 confusion_recorded: failed boundary case"])

    assert "shared features" in distinction_text
    assert "broad encyclopedia" in distinction_text
    assert "one question at a time" in test_text
    assert "minimal counterexamples" in misconception_text
    assert "deterministic local evidence" in temporal_text

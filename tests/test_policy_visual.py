from __future__ import annotations

from pathlib import Path

from ailearn.models import ClassificationPolicy, Goal, PositionDecision, VisualResourceRecord
from ailearn.prompts import (
    classify_with_policy_prompt,
    refine_policy_prompt,
    visual_explanation_prompt,
    visual_suggestion_prompt,
)
from ailearn.review import generate_weekly_review
from ailearn.status import suggest_next_actions
from ailearn.storage import init_project, load_yaml_model, save_yaml_model


def sample_goal() -> Goal:
    return Goal(
        id="goal_policy",
        title="Quantum learning policy",
        main_goal="Read topological order papers with reliable quantum mechanics language",
        stage_goal="Classify encountered tools by current research-reading need",
        transfer_goal="Use distinctions and derivations in new condensed matter papers",
        external_goal="Research preparation",
        priority_topics=["density_matrix", "superposition_state"],
    )


def test_classification_policy_schema_and_position_policy_reference_round_trip(tmp_path: Path):
    init_project(tmp_path)
    goal = sample_goal()
    policy = ClassificationPolicy(
        id="policy_qm",
        goal_id=goal.id,
        title="QM for topological order policy",
        description="A/B/C is a dynamic classification grammar for this goal.",
        a_zone_criteria=["Core disciplinary language used without AI."],
        b_zone_criteria=["Must know role and relation; details can be restored."],
        c_zone_criteria=["Index recall is enough for now."],
        core_tool_criteria=["Appears in derivations or paper arguments repeatedly."],
        non_core_tool_criteria=["Useful but not a trust bottleneck."],
        test_mode_criteria=["A-zone items and heavy tools need tests."],
        upgrade_triggers=["Repeated confusion or paper dependence."],
        downgrade_triggers=["Only needed as lookup metadata."],
        revisit_triggers=["After reading a paper using the concept centrally."],
        examples_optional=["density_matrix -> A while reading mixed-state papers"],
    )
    position = PositionDecision(
        id="pos_policy",
        goal_id=goal.id,
        policy_id=policy.id,
        knowledge_point="density_matrix",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Policy marks it as core paper language.",
        confidence="high",
        epistemic_status="learning_strategy",
        internalization_level="A0",
    )

    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "policies" / f"{policy.id}.yaml", policy)
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)

    loaded_policy = load_yaml_model(tmp_path / "data" / "policies" / f"{policy.id}.yaml", ClassificationPolicy)
    loaded_position = load_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", PositionDecision)

    assert loaded_policy.title == "QM for topological order policy"
    assert loaded_position.policy_id == policy.id


def test_policy_prompts_treat_abc_as_dynamic_classification_language():
    goal = sample_goal()
    policy = ClassificationPolicy(
        id="policy_prompt",
        goal_id=goal.id,
        title="Prompt policy",
        description="Classify only encountered knowledge points.",
        a_zone_criteria=["Must be internalized."],
        b_zone_criteria=["Positioning only."],
        c_zone_criteria=["Index recall."],
        core_tool_criteria=["Needed in derivations."],
        non_core_tool_criteria=["Supporting tool."],
        test_mode_criteria=["A/heavy records need testing."],
        upgrade_triggers=["Repeated use."],
        downgrade_triggers=["No longer central."],
        revisit_triggers=["Goal changes."],
        examples_optional=[],
    )

    refine = refine_policy_prompt(goal)
    classify = classify_with_policy_prompt(
        goal,
        "density_matrix",
        policy,
        current_user_state="can use notation but cannot explain mixed states",
        reference_hints="Sakurai and Nielsen-Chuang both appear in local references.",
    )

    assert "classification grammar" in refine
    assert "not a fixed map" in refine
    assert "collide" in classify
    assert "active learning goal" in classify
    assert "classification policy" in classify
    assert "learning strategy judgment" in classify
    assert "recommended A/B/C position" in classify


def test_visual_resource_schema_storage_and_prompts(tmp_path: Path):
    init_project(tmp_path)
    goal = sample_goal()
    visual = VisualResourceRecord(
        id="visual_density_matrix",
        goal_id=goal.id,
        topic="density_matrix",
        title="Bloch sphere mixed-state schematic",
        visual_type="ai_generated_schematic",
        source_priority="ai_generated",
        source_url_or_path="",
        source_detail="Teaching schematic only.",
        reliability="low",
        usage="explanation",
        why_needed="The geometry is repeatedly confusing.",
        related_record_ids=["pos_policy"],
        copyright_note="Illustrative, not evidence.",
    )

    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "visuals" / f"{visual.id}.yaml", visual)
    loaded = load_yaml_model(tmp_path / "data" / "visuals" / f"{visual.id}.yaml", VisualResourceRecord)

    suggest = visual_suggestion_prompt(goal, "density_matrix")
    explain = visual_explanation_prompt(goal, loaded)

    assert loaded.visual_type == "ai_generated_schematic"
    assert "paper / textbook / lecture note" in suggest
    assert "teaching aids, not evidence" in suggest
    assert "search keywords or source suggestions" in suggest
    assert "AI-generated" in explain
    assert "not evidence" in explain


def test_visual_support_appears_in_next_actions_and_weekly_review(tmp_path: Path):
    init_project(tmp_path)
    goal = sample_goal()
    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    (tmp_path / "data" / "distinctions" / "dist_visual.yaml").write_text(
        """
id: dist_visual
goal_id: goal_policy
title: superposition vs entanglement
concepts:
- superposition_state
- entangled_state
confusion_statement: I keep treating any superposition as entanglement.
status: needs_test
internalization_target: A2
record_intensity: medium
confusion_count: 3
related_claim_ids: []
related_test_ids: []
related_session_ids: []
created_at: 2026-05-26T00:00:00+00:00
updated_at: 2026-05-26T00:00:00+00:00
next_action: ""
""",
        encoding="utf-8",
    )

    actions = suggest_next_actions(tmp_path, limit=10)
    review_path = generate_weekly_review(tmp_path)
    review = review_path.read_text(encoding="utf-8")

    assert any("visual" in action.lower() for action in actions)
    assert "Visual Support Suggestions" in review
    assert "superposition vs entanglement" in review

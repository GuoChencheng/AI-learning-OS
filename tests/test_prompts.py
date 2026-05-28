from ailearn.models import ClaimRecord, DerivationRecord, Goal
from ailearn.prompts import (
    claim_verification_prompt,
    deep_research_prompt,
    derivation_guidance_prompt,
    dynamic_positioning_prompt,
    extract_positioning_from_research_prompt,
    extract_references_prompt,
    goal_intake_prompt,
    method_router_prompt,
    socratic_drill_prompt,
    test_topic_prompt,
    weekly_review_prompt,
)


def sample_goal() -> Goal:
    return Goal(
        id="goal_prompt",
        title="Quantum mechanics research prep",
        main_goal="Build reliable perturbation theory intuition",
        stage_goal="Compare approximation methods",
        transfer_goal="Use ideas in condensed matter papers",
        external_goal="Prepare for qualifying exam",
        priority_topics=["perturbation_theory"],
    )


def test_dynamic_positioning_prompt_contains_goal_and_classification_contract():
    prompt = dynamic_positioning_prompt(
        sample_goal(),
        "density_matrix",
        current_context="Studying mixed states and decoherence.",
    )

    assert "Quantum mechanics research prep" in prompt
    assert "density_matrix" in prompt
    assert "A_no_ai_internalization" in prompt
    assert "B_knowledge_positioning" in prompt
    assert "C_index_recall" in prompt
    assert "core_tool" in prompt
    assert "learning_strategy" in prompt


def test_claim_verification_prompt_demands_epistemic_distinctions():
    claim = ClaimRecord(
        id="claim_prompt",
        goal_id="goal_prompt",
        text="Perturbation theory can be seen as a low-order expansion of effective theory.",
        context="Comparing approximation methods",
        type="interpretation",
        status="unverified",
        epistemic_status="inference",
        strict_part="",
        caveat="",
        counterexample_or_boundary="",
        next_action="Verify",
    )

    prompt = claim_verification_prompt(sample_goal(), claim)

    assert "strict fact" in prompt
    assert "derived result" in prompt
    assert "standard interpretation" in prompt
    assert "wrong or misleading" in prompt
    assert claim.text in prompt


def test_derivation_guidance_prompt_asks_for_one_step_without_full_solution():
    derivation = DerivationRecord(
        id="der_prompt",
        goal_id="goal_prompt",
        topic="nondegenerate_perturbation_theory",
        importance="core_tool",
        status="partial",
        result_to_trust="First-order energy correction",
        user_derived_steps=[],
        ai_hinted_steps=[],
        not_yet_trusted=["Projection step"],
        next_action="Try again",
    )

    prompt = derivation_guidance_prompt(sample_goal(), derivation)

    assert "do not give the full derivation immediately" in prompt
    assert "one step at a time" in prompt
    assert "user-completed steps" in prompt
    assert "AI-hinted steps" in prompt


def test_socratic_and_weekly_prompts_are_copyable_contracts():
    socratic = socratic_drill_prompt(sample_goal(), "density_matrix")
    weekly = weekly_review_prompt()

    assert "ask one question at a time" in socratic
    assert "do not answer unless asked" in socratic
    assert "clear / incomplete / misleading / wrong" in socratic
    assert "unresolved claims" in weekly
    assert "derivations needing rework" in weekly


def test_goal_intake_prompt_asks_for_learning_strategy_not_final_truth():
    prompt = goal_intake_prompt("I want to learn topological order for research reading.")

    assert "main goal" in prompt
    assert "stage goal" in prompt
    assert "transfer goal" in prompt
    assert "desired depth" in prompt
    assert "learning enough" in prompt
    assert "learning strategy, not final truth" in prompt


def test_deep_research_prompt_frames_output_as_initial_guidance():
    prompt = deep_research_prompt(sample_goal())

    assert "ChatGPT Deep Research" in prompt
    assert "global course/topic map" in prompt
    assert "initial A/B/C knowledge split" in prompt
    assert "core tools / non-core tools" in prompt
    assert "references folder" in prompt
    assert "initial guidance" in prompt
    assert "must not be treated as final truth" in prompt


def test_extract_prompts_use_import_content_as_suggestions_only():
    research = "# Research\nUse Sakurai and lecture notes. Density matrices are central."

    refs = extract_references_prompt("import_20260526", research)
    positioning = extract_positioning_from_research_prompt("import_20260526", research)

    assert "ReferenceRecord" in refs
    assert "reference_type" in refs
    assert "usage_stage" in refs
    assert "suggestions only" in refs
    assert "A_no_ai_internalization" in positioning
    assert "core tools" in positioning
    assert "revisit triggers" in positioning
    assert "suggestions only" in positioning


def test_method_router_prompt_asks_for_method_not_full_teaching():
    prompt = method_router_prompt(
        sample_goal(),
        state="formula_without_trust",
        topic="perturbation_theory",
        local_actions=["derivation trust", "Socratic drill"],
    )

    assert "formula_without_trust" in prompt
    assert "perturbation_theory" in prompt
    assert "choose a learning method" in prompt
    assert "do not teach the whole topic" in prompt
    assert "derivation trust" in prompt


def test_test_topic_prompt_covers_internalization_ladder():
    prompt = test_topic_prompt(sample_goal(), "perturbation_theory")

    assert "no-AI explanation" in prompt
    assert "boundary/counterexample" in prompt
    assert "key derivation reconstruction" in prompt
    assert "transfer question" in prompt
    assert "A1" in prompt
    assert "A4" in prompt

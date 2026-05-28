from __future__ import annotations

import json
from pathlib import Path

import yaml

from ailearn.context import build_context_pack, context_policy_text
from ailearn.indexes import refresh_indexes
from ailearn.models import (
    ClaimRecord,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    SessionFootprint,
    TestRecord,
)
from ailearn.prompts import prompt_with_context_reference
from ailearn.storage import init_project, save_session, save_yaml_model
from ailearn.validate import validate_project


def seed_context_project(root: Path) -> None:
    init_project(root)
    goal = Goal(
        id="goal_context",
        title="Context Goal",
        main_goal="Read perturbation theory papers",
        stage_goal="Trust nondegenerate perturbation theory",
        transfer_goal="Use perturbative arguments in condensed matter",
        external_goal="Research reading",
        priority_topics=["perturbation_theory", "density_matrix"],
    )
    claim = ClaimRecord(
        id="claim_context",
        goal_id=goal.id,
        text="Perturbation theory is a low-order effective theory.",
        context="perturbation_theory session",
        type="interpretation",
        status="unverified",
        epistemic_status="inference",
        record_intensity="heavy",
        next_action="Verify boundary conditions.",
    )
    derivation = DerivationRecord(
        id="der_context",
        goal_id=goal.id,
        topic="perturbation_theory",
        importance="core_tool",
        status="needs_rederive",
        result_to_trust="Second-order energy correction",
        record_intensity="heavy",
    )
    position = PositionDecision(
        id="pos_context",
        goal_id=goal.id,
        knowledge_point="perturbation_theory",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core paper-reading tool.",
        confidence="medium",
        epistemic_status="learning_strategy",
        internalization_level="A0",
        revisit_when=["before effective Hamiltonians"],
    )
    reference = ReferenceRecord(
        id="ref_context",
        goal_id=goal.id,
        title="Perturbation Notes",
        authors_or_source="Course",
        reference_type="lecture_note",
        path_or_url="refs/perturbation.pdf",
        topics=["perturbation_theory"],
        relevance_to_goal="Metadata only for context loading.",
        usage_stage="core_learning",
        reading_status="unread",
        notes="Do not include full paper text in default context packs.",
    )
    test = TestRecord(
        id="test_context",
        goal_id=goal.id,
        topic="perturbation_theory",
        position_id=position.id,
        test_type="derivation_reconstruction",
        status="planned",
        internalization_target="A3",
        prompt="Reconstruct the derivation without AI.",
    )
    distinction = DistinctionRecord(
        id="dist_context",
        goal_id=goal.id,
        title="perturbation vs effective theory",
        concepts=["perturbation_theory", "effective_theory"],
        confusion_statement="I blur approximation order with model reduction.",
        status="needs_test",
        related_claim_ids=[claim.id],
    )
    misconception = MisconceptionRecord(
        id="misc_context",
        goal_id=goal.id,
        statement="All effective theories are perturbation theory.",
        why_wrong="Effective theories can be non-perturbative.",
        corrected_view="Perturbation is one method; effective theory is broader.",
        related_topics=["perturbation_theory"],
        severity="important",
        status="recurring",
        recurrence_count=2,
    )
    session = SessionFootprint(
        id="session_context",
        goal_id=goal.id,
        topic="perturbation_theory",
        mode="derivation",
        learning_state="formula_without_trust",
        references_used=[reference.id],
    )
    for directory, record in [
        ("goals", goal),
        ("claims", claim),
        ("derivations", derivation),
        ("positioning", position),
        ("references", reference),
        ("tests", test),
        ("distinctions", distinction),
        ("misconceptions", misconception),
    ]:
        save_yaml_model(root / "data" / directory / f"{record.id}.yaml", record)
    save_session(root / "data" / "sessions" / f"{session.id}.md", session, {"Started with": "Formula trust gap"})
    (root / "data" / "research_imports" / "deep.md").write_text("Very long Deep Research body should not be loaded.", encoding="utf-8")


def test_core_protocol_docs_exist_and_define_minimal_context():
    core = Path("docs/core_methodology.md")
    protocol = Path("docs/ai_context_protocol.md")

    assert core.is_file()
    assert protocol.is_file()
    assert "minimal context" in core.read_text(encoding="utf-8").lower()
    assert "task type" in protocol.read_text(encoding="utf-8").lower()


def test_refresh_indexes_writes_manifest_topic_index_and_open_loops(tmp_path: Path):
    seed_context_project(tmp_path)

    paths = refresh_indexes(tmp_path)

    assert paths.manifest.is_file()
    manifest_lines = [json.loads(line) for line in paths.manifest.read_text(encoding="utf-8").splitlines()]
    claim_line = next(line for line in manifest_lines if line["id"] == "claim_context")
    assert claim_line["type"] == "claims"
    assert claim_line["epistemic_status"] == "inference"
    assert claim_line["path"].endswith("claim_context.yaml")

    topic_index = yaml.safe_load(paths.topic_index.read_text(encoding="utf-8"))
    assert "perturbation_theory" in topic_index
    assert "claim_context" in topic_index["perturbation_theory"]["claims"]
    assert "der_context" in topic_index["perturbation_theory"]["derivations"]
    assert "session_context" in topic_index["perturbation_theory"]["sessions"]

    open_loops = paths.open_loops.read_text(encoding="utf-8")
    assert "Unverified Claims" in open_loops
    assert "claim_context" in open_loops
    assert "dist_context" in open_loops
    assert "misc_context" in open_loops


def test_context_pack_for_verify_claim_is_compact_and_task_specific(tmp_path: Path):
    seed_context_project(tmp_path)
    refresh_indexes(tmp_path)

    pack = build_context_pack(tmp_path, task_type="verify_claim", record_id="claim_context", budget="small")
    text = pack.path.read_text(encoding="utf-8")

    assert "AI Context Pack" in text
    assert "Task type: verify_claim" in text
    assert "claim_context" in text
    assert "Perturbation theory is a low-order effective theory." in text
    assert "Do not read all files" in text
    assert "Very long Deep Research body should not be loaded" not in text
    assert len(text) < 12000


def test_context_pack_for_test_topic_respects_budget(tmp_path: Path):
    seed_context_project(tmp_path)
    refresh_indexes(tmp_path)

    small = build_context_pack(tmp_path, task_type="test_topic", topic="perturbation_theory", budget="small")
    large = build_context_pack(tmp_path, task_type="test_topic", topic="perturbation_theory", budget="large")

    small_text = small.path.read_text(encoding="utf-8")
    large_text = large.path.read_text(encoding="utf-8")
    assert "claim_context" in small_text
    assert "der_context" in small_text
    assert len(small_text) <= len(large_text)
    assert "Selected Session Excerpts" not in small_text
    assert "Selected Session Excerpts" in large_text


def test_context_policy_and_prompt_context_reference(tmp_path: Path):
    seed_context_project(tmp_path)
    refresh_indexes(tmp_path)
    pack = build_context_pack(tmp_path, task_type="derivation_guidance", record_id="der_context", budget="medium")

    policy = context_policy_text()
    prompt = prompt_with_context_reference("Base prompt", pack.path)

    assert "identify task type" in policy.lower()
    assert str(pack.path) in prompt
    assert "Do not read all local files" in prompt


def test_validate_project_accepts_generated_indexes_and_context_pack(tmp_path: Path):
    seed_context_project(tmp_path)
    refresh_indexes(tmp_path)
    build_context_pack(tmp_path, task_type="verify_claim", record_id="claim_context", budget="medium")

    report = validate_project(tmp_path)

    assert report.ok

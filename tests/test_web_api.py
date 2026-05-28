from pathlib import Path

import yaml

from ailearn.models import (
    ClaimRecord,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    TestRecord,
)
from ailearn.storage import init_project, save_yaml_model
from ailearn.web_api import handle_api_request


def seed_api_project(tmp_path: Path) -> None:
    init_project(tmp_path)
    goal = Goal(
        id="goal_api",
        title="API Goal",
        main_goal="Read papers",
        stage_goal="Build tools",
        transfer_goal="Use in research",
        external_goal="Seminar",
        priority_topics=["density_matrix"],
    )
    claim = ClaimRecord(
        id="claim_api",
        goal_id=goal.id,
        text="A student claim",
        context="test",
        type="hypothesis",
        status="unverified",
        epistemic_status="speculation",
        record_intensity="medium",
    )
    save_yaml_model(tmp_path / "data" / "goals" / f"{goal.id}.yaml", goal)
    save_yaml_model(tmp_path / "data" / "claims" / f"{claim.id}.yaml", claim)
    position = PositionDecision(
        id="pos_api",
        goal_id=goal.id,
        knowledge_point="density_matrix",
        position="A_no_ai_internalization",
        tool_role="core_tool",
        reason="Core paper language.",
        confidence="medium",
        epistemic_status="learning_strategy",
        internalization_level="A0",
        record_intensity="heavy",
        revisit_when=["before entanglement entropy"],
    )
    derivation = DerivationRecord(
        id="der_api",
        goal_id=goal.id,
        topic="density_matrix",
        importance="core_tool",
        status="needs_rederive",
        result_to_trust="Trace rule",
        record_intensity="heavy",
    )
    test = TestRecord(
        id="test_api",
        goal_id=goal.id,
        topic="density_matrix",
        test_type="mixed",
        status="planned",
        internalization_target="A3",
        prompt="Explain without AI.",
    )
    reference = ReferenceRecord(
        id="ref_api",
        goal_id=goal.id,
        title="Density Matrix Notes",
        authors_or_source="Course",
        reference_type="lecture_note",
        path_or_url="refs/density.pdf",
        topics=["density_matrix"],
        relevance_to_goal="Core source for density matrix language.",
        usage_stage="core_learning",
        reading_status="unread",
    )
    save_yaml_model(tmp_path / "data" / "positioning" / f"{position.id}.yaml", position)
    save_yaml_model(tmp_path / "data" / "derivations" / f"{derivation.id}.yaml", derivation)
    save_yaml_model(tmp_path / "data" / "tests" / f"{test.id}.yaml", test)
    save_yaml_model(tmp_path / "data" / "references" / f"{reference.id}.yaml", reference)
    distinction = DistinctionRecord(
        id="dist_api",
        goal_id=goal.id,
        title="pure vs mixed state",
        concepts=["pure_state", "mixed_state"],
        confusion_statement="Cannot separate state vector from density matrix language.",
        status="needs_distinction",
    )
    misconception = MisconceptionRecord(
        id="misc_api",
        goal_id=goal.id,
        statement="Every density matrix is a mixed state.",
        why_wrong="Pure states also have density matrices.",
        corrected_view="Density matrices can represent pure or mixed states.",
        related_topics=["density_matrix"],
        severity="important",
        status="active",
    )
    save_yaml_model(tmp_path / "data" / "distinctions" / f"{distinction.id}.yaml", distinction)
    save_yaml_model(tmp_path / "data" / "misconceptions" / f"{misconception.id}.yaml", misconception)


def test_api_lists_goals_and_active_goal(tmp_path: Path):
    seed_api_project(tmp_path)

    goals = handle_api_request("GET", "/api/goals", None, tmp_path)
    active = handle_api_request("GET", "/api/goals/active", None, tmp_path)

    assert goals.status == 200
    assert goals.data["items"][0]["id"] == "goal_api"
    assert active.status == 200
    assert active.data["item"]["title"] == "API Goal"


def test_api_claims_and_prompt_endpoint(tmp_path: Path):
    seed_api_project(tmp_path)

    claims = handle_api_request("GET", "/api/claims?status=unverified", None, tmp_path)
    prompt = handle_api_request(
        "POST",
        "/api/prompts/claim-verification",
        {"claim_id": "claim_api"},
        tmp_path,
    )

    assert claims.status == 200
    assert claims.data["items"][0]["text"] == "A student claim"
    assert prompt.status == 200
    assert "strict fact" in prompt.data["prompt"]
    assert "A student claim" in prompt.data["prompt"]


def test_api_status_validation_and_review(tmp_path: Path):
    seed_api_project(tmp_path)

    dashboard = handle_api_request("GET", "/api/dashboard", None, tmp_path)
    validation = handle_api_request("GET", "/api/validate", None, tmp_path)
    review = handle_api_request("POST", "/api/reviews/weekly", {}, tmp_path)

    assert dashboard.status == 200
    assert dashboard.data["status"]["active_goal_title"] == "API Goal"
    assert dashboard.data["next_actions"]
    assert validation.status == 200
    assert validation.data["ok"] is True
    assert review.status == 200
    assert review.data["path"].endswith(".md")


def test_api_lists_distinctions_misconceptions_and_prompts(tmp_path: Path):
    seed_api_project(tmp_path)

    distinctions = handle_api_request("GET", "/api/distinctions", None, tmp_path)
    misconceptions = handle_api_request("GET", "/api/misconceptions", None, tmp_path)
    prompt = handle_api_request("POST", "/api/prompts/distinguish", {"distinction_id": "dist_api"}, tmp_path)
    correction = handle_api_request("POST", "/api/prompts/misconception-correction", {"misconception_id": "misc_api"}, tmp_path)

    assert distinctions.status == 200
    assert distinctions.data["items"][0]["title"] == "pure vs mixed state"
    assert misconceptions.status == 200
    assert "shared features" in prompt.data["prompt"]
    assert "why the statement is wrong" in correction.data["prompt"]


def test_api_event_timeline_endpoint(tmp_path: Path):
    seed_api_project(tmp_path)
    created = handle_api_request(
        "POST",
        "/api/distinctions",
        {
            "title": "superposition vs entanglement",
            "concepts": ["superposition", "entanglement"],
            "confusion_statement": "They feel identical.",
            "status": "needs_distinction",
        },
        tmp_path,
    )

    timeline = handle_api_request("GET", f"/api/events/timeline/{created.data['item']['id']}", None, tmp_path)

    assert created.status == 201
    assert timeline.status == 200
    assert any("record_created" in line for line in timeline.data["timeline"])


def test_api_dashboard_view_is_learning_cockpit_not_raw_tables(tmp_path: Path):
    seed_api_project(tmp_path)

    response = handle_api_request("GET", "/api/dashboard-view", None, tmp_path)

    assert response.status == 200
    data = response.data
    assert data["active_goal"]["id"] == "goal_api"
    assert data["primary_next_action"]["action_type"] == "verify_claim"
    assert data["primary_next_action"]["related_record_ids"] == ["claim_api"]
    assert data["open_loop_counts"]["unverified_claims"] == 1
    assert data["open_loop_counts"]["trust_gaps"] == 1
    assert any(item["id"] == "pos_api" for item in data["ready_for_test"])
    assert any(item["id"] == "ref_api" for item in data["recent_references"])


def test_api_learning_items_unifies_position_distinction_misconception_derivation_and_test(tmp_path: Path):
    seed_api_project(tmp_path)

    response = handle_api_request("GET", "/api/learning-items", None, tmp_path)

    assert response.status == 200
    items = response.data["items"]
    by_id = {item["id"]: item for item in items}
    assert by_id["pos_api"]["source_type"] == "position"
    assert by_id["pos_api"]["title"] == "density_matrix"
    assert by_id["pos_api"]["internalization_level"] == "A0"
    assert by_id["dist_api"]["source_type"] == "distinction"
    assert by_id["misc_api"]["source_type"] == "misconception"
    assert by_id["der_api"]["source_type"] == "derivation"
    assert by_id["test_api"]["source_type"] == "test"


def test_api_provider_settings_hide_keys_and_expose_prompt_only(tmp_path: Path):
    seed_api_project(tmp_path)
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "prompt_only": True,
                "default_provider": "mock",
                "providers": {
                    "mock": {
                        "type": "openai_compatible",
                        "base_url": "https://example.invalid/v1",
                        "api_key_env": "MISSING_TEST_KEY",
                        "default_model": "test-model",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    response = handle_api_request("GET", "/api/settings/providers", None, tmp_path)

    assert response.status == 200
    assert response.data["prompt_only"] is True
    provider = response.data["providers"][0]
    assert provider["id"] == "mock"
    assert provider["api_key_env"] == "MISSING_TEST_KEY"
    assert "api_key" not in provider

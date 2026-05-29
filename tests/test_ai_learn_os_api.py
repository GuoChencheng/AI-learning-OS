from __future__ import annotations

from pathlib import Path

from ailearn.api.app import create_app
from ailearn.api.testing import TestClient
from ailearn.db.database import Database
from ailearn.model_gateway.fake import FakeModelGateway


def make_client(tmp_path: Path) -> TestClient:
    database = Database(f"sqlite:///{tmp_path / 'learnos.sqlite3'}")
    database.init()
    app = create_app(database=database, model_gateway=FakeModelGateway())
    return TestClient(app)


def test_chat_endpoint_runs_full_pipeline_and_writes_state(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics", "description": "Critical phenomena"}).json()

    response = client.post(
        "/api/chat",
        json={
            "project_id": project["id"],
            "message": "二阶相变处一定是 CFT 吗？",
            "selected_mode": "auto",
            "button_action": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    assert data["suggested_next_action"]
    assert [step["agent"] for step in data["pipeline_trace"]["steps"]] == [
        "request_intake",
        "project_resolver",
        "context_extractor",
        "context_pack_builder",
        "state_judge",
        "module_router",
        "answer_composer",
        "state_writer",
    ]
    assert data["state_updates"]["claims"]
    assert data["state_updates"]["distinctions"]
    assert data["state_updates"]["review_triggers"]

    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert len(state["claims"]) == 1
    assert len(state["distinctions"]) == 1
    assert len(state["review_triggers"]) == 1


def test_run_next_uses_priority_order_for_due_review_trigger(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Math", "description": "Algebra"}).json()
    client.post(
        f"/api/projects/{project['id']}/review-triggers",
        json={
            "target": "eigenvalue vs eigenvector",
            "trigger_reason": "due now",
            "review_type": "distinguish",
            "scheduled_time": "2000-01-01T00:00:00Z",
            "success_criteria": "Explain the boundary.",
        },
    )

    response = client.post("/api/run-next", json={"project_id": project["id"]})

    assert response.status_code == 200
    data = response.json()
    assert data["chosen_module"] == "review_point_runner"
    assert "Review Trigger" in data["reason"]
    assert data["pipeline_trace"]["decision"]["priority"] == "due_review_trigger"


def test_project_settings_system_settings_references_and_revert(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Research", "mode": "research"}).json()

    settings = client.patch(
        f"/api/projects/{project['id']}/settings",
        json={"teaching_style": "concise", "enabled_modules": ["concept_explainer", "review_point_runner"]},
    ).json()
    assert settings["teaching_style"] == "concise"

    system = client.patch("/api/system-settings", json={"default_language": "zh", "theme": "light"}).json()
    assert system["default_language"] == "zh"

    ref = client.post(
        f"/api/projects/{project['id']}/references",
        json={
            "title": "Mini note",
            "source_type": "manual",
            "reliability_level": "high",
            "scope": "test",
            "text": "Alpha beta gamma. " * 80,
        },
    ).json()
    chunks = client.get(f"/api/references/{ref['id']}/chunks").json()
    assert len(chunks["items"]) >= 2

    chat = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "Explain alpha", "selected_mode": "explain"},
    ).json()
    log_id = chat["state_updates"]["log_id"]
    reverted = client.post(f"/api/state-updates/{log_id}/revert").json()
    assert reverted["status"] == "reverted"
    claims = client.get(f"/api/projects/{project['id']}/claims").json()["items"]
    assert claims[0]["status"] == "deprecated"

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ailearn.api.app import create_app
from ailearn.api.testing import TestClient
from ailearn.db.database import Database
from ailearn.db.repository import Repository
from ailearn.model_gateway.fake import FakeModelGateway


def make_client_and_repo(tmp_path: Path) -> tuple[TestClient, Repository]:
    database = Database(f"sqlite:///{tmp_path / 'learnos.sqlite3'}")
    database.init()
    app = create_app(database=database, model_gateway=FakeModelGateway())
    return TestClient(app), Repository(database)


def make_client(tmp_path: Path) -> TestClient:
    client, _ = make_client_and_repo(tmp_path)
    return client


def test_test_client_uses_fastapi_core_state_when_available(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'fastapi-wrapper.sqlite3'}")
    database.init()
    app = create_app(database=database, model_gateway=FakeModelGateway())
    core = getattr(getattr(app, "state", None), "ai_learn_core", app)
    fastapi_like_wrapper = SimpleNamespace(state=SimpleNamespace(ai_learn_core=core))

    project = TestClient(fastapi_like_wrapper).post("/api/projects", json={"name": "Wrapper"}).json()

    assert project["id"].startswith("proj_")
    assert project["name"] == "Wrapper"


def test_chat_endpoint_runs_full_pipeline_and_writes_selective_state(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
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
    assert data["model_path"] == "fallback"
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
    assert state["knowledge_positions"] == []
    assert state["derivation_trust_records"] == []
    assert repo.list_by_project("context_packs", project["id"]) == []

    logs = repo.list_by_project("state_update_logs", project["id"])
    payload = logs[0]["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    assert payload["source_metadata"]["source_message_id"] == data["pipeline_trace"]["message_ids"]["user"]
    assert payload["source_metadata"]["source_type"] == "user_question"
    assert payload["created"]["claims"]
    assert payload["discarded_ephemeral_judgments"]


def test_seed_cft_project_endpoint_creates_demo_project(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post("/api/projects/seed/cft", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["project_id"] == data["project"]["id"]
    assert data["project"]["name"] == "我要学习 CFT"
    state = client.get(f"/api/projects/{data['project_id']}/state").json()
    refs = client.get(f"/api/projects/{data['project_id']}/references").json()
    assert state["claims"]
    assert state["distinctions"]
    assert state["knowledge_positions"]
    assert state["derivation_trust_records"]
    assert state["review_triggers"]
    assert refs["items"]


def test_context_pack_persistence_debug_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_LEARN_DEBUG_PERSIST_CONTEXT", "1")
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Debug Context"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "What is CFT?"})

    assert response.status_code == 200
    persisted = repo.list_by_project("context_packs", project["id"])
    assert len(persisted) == 1
    assert persisted[0]["current_request"] == "What is CFT?"


def test_greeting_does_not_over_record_learning_state(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Greeting"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "你好"})

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert state["claims"] == []
    assert state["distinctions"] == []
    assert state["review_triggers"] == []


def test_operational_message_does_not_create_learning_records(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Ops"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "把回答简洁一点"})

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert state["claims"] == []
    assert state["distinctions"] == []
    assert state["review_triggers"] == []


def test_comparison_confusion_question_creates_distinction(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Boundary"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "临界点和 CFT 描述有什么区别？"})

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert len(state["distinctions"]) == 1
    assert len(state["review_triggers"]) == 1


def test_derivation_mode_creates_derivation_trust_record(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "Derivation"}).json()

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "推导平均场临界指数", "selected_mode": "derive"},
    )

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert len(state["derivation_trust_records"]) == 1
    assert state["knowledge_positions"] == []


def test_no_ai_mode_creates_knowledge_position_update(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project = client.post("/api/projects", json={"name": "No AI"}).json()

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "测试我是否能不用 AI 解释 CFT", "button_action": "no_ai_test"},
    )

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert len(state["knowledge_positions"]) == 1


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
    assert data["priority"] == "due_review_trigger"
    assert data["loop_step"] == "review"
    assert data["why_this_now"]
    assert data["expected_user_action"]
    assert data["will_update"] == ["temporal_trace", "review_trigger_status"]


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

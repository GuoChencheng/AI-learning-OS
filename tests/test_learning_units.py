from __future__ import annotations

from pathlib import Path

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


def test_chat_socratic_creates_learning_unit(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics"}).json()

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？", "selected_mode": "socratic"},
    )

    assert response.status_code == 200
    data = response.json()
    unit = data["active_learning_unit"]
    assert unit["status"] == "active"
    assert unit["method"] == "socratic_questioner"
    assert unit["turn_count"] >= 1
    assert data["pipeline_trace"]["learning_unit"]["action"] == "create_new_unit"
    assert data["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is True

    active = repo.get_active_learning_unit(project["id"])
    assert active is not None
    assert active["id"] == unit["id"]
    assert active["context_snapshot_json"]
    assert len(repo.list_learning_unit_turns(unit["id"])) == 2


def test_chat_reuses_learning_unit_without_full_context_extraction(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics"}).json()
    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？", "selected_mode": "socratic"},
    ).json()

    second = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "那这个条件为什么重要？", "selected_mode": "auto"},
    ).json()

    assert second["active_learning_unit"]["id"] == first["active_learning_unit"]["id"]
    assert second["pipeline_trace"]["learning_unit"]["action"] == "reuse_active_unit"
    assert second["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is False
    assert second["pipeline_trace"]["learning_unit"]["turn_count"] >= 2
    assert len(repo.list_learning_unit_turns(first["active_learning_unit"]["id"])) == 4


def test_manual_method_switch_closes_old_unit_and_creates_new_one(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics"}).json()
    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？", "selected_mode": "socratic"},
    ).json()

    second = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "推导平均场临界指数", "button_action": "derive"},
    ).json()

    old_unit = repo.get_by_id("learning_units", first["active_learning_unit"]["id"])
    assert old_unit is not None
    assert old_unit["status"] == "closed"
    assert old_unit["close_reason"] == "manual_method_switch"
    assert second["active_learning_unit"]["id"] != old_unit["id"]
    assert second["active_learning_unit"]["method"] == "derivation_coach"
    assert second["pipeline_trace"]["learning_unit"]["action"] == "close_and_create_new"


def test_user_can_close_learning_unit(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics"}).json()
    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？", "selected_mode": "socratic"},
    ).json()

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "结束这个小单元，总结一下", "selected_mode": "auto"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_learning_unit"] is None
    assert data["pipeline_trace"]["learning_unit"]["action"] == "no_unit"
    closed = repo.get_by_id("learning_units", first["active_learning_unit"]["id"])
    assert closed is not None
    assert closed["status"] == "closed"
    assert closed["unit_summary"]
    assert repo.get_active_learning_unit(project["id"]) is None


def test_run_next_creates_or_continues_learning_unit(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Math", "description": "Algebra"}).json()

    first = client.post("/api/run-next", json={"project_id": project["id"]}).json()
    assert first["active_learning_unit"]
    assert first["active_learning_unit"]["method"] == first["chosen_module"]

    second = client.post("/api/run-next", json={"project_id": project["id"]}).json()
    assert second["active_learning_unit"]["id"] == first["active_learning_unit"]["id"]
    assert second["pipeline_trace"]["learning_unit"]["action"] == "reuse_active_unit"
    assert repo.get_active_learning_unit(project["id"])["id"] == first["active_learning_unit"]["id"]


def test_learning_unit_api_endpoints(tmp_path: Path) -> None:
    client, _ = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Physics"}).json()
    chat = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？", "selected_mode": "socratic"},
    ).json()
    unit_id = chat["active_learning_unit"]["id"]

    active = client.get(f"/api/projects/{project['id']}/learning-units/active").json()
    assert active["item"]["id"] == unit_id

    listed = client.get(f"/api/projects/{project['id']}/learning-units").json()
    assert listed["items"][0]["id"] == unit_id

    refreshed = client.post(f"/api/projects/{project['id']}/learning-units/{unit_id}/refresh-context").json()
    assert refreshed["context_snapshot_json"]["refresh_requested"] is True

    follow_up = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "继续这个问题", "selected_mode": "auto"},
    ).json()
    assert follow_up["active_learning_unit"]["id"] == unit_id
    assert follow_up["pipeline_trace"]["learning_unit"]["action"] == "refresh_unit_context"
    assert follow_up["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is True

    closed = client.post(f"/api/projects/{project['id']}/learning-units/{unit_id}/close").json()
    assert closed["status"] == "closed"
    assert closed["close_reason"] == "user_closed"

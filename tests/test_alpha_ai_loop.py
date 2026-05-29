from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ailearn.api.app import create_app, create_core_app
from ailearn.api.testing import TestClient
from ailearn.agents.contracts import AnswerComposerOutput, StateWriterOutput
from ailearn.db.database import Database
from ailearn.db.repository import Repository
from ailearn.model_gateway.base import ModelGateway, ModelGatewayError, ModelTier
from ailearn.model_gateway.fake import FakeModelGateway
from ailearn.model_gateway.openai_compatible import OpenAICompatibleGateway


class SpyStructuredGateway(ModelGateway):
    def __init__(self, outputs: dict[type[Any], dict[str, Any] | str] | None = None, fail: bool = False) -> None:
        self.outputs = outputs or {}
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def complete(self, prompt: str, tier: ModelTier = ModelTier.FAST) -> str:
        self.calls.append({"prompt": prompt, "tier": tier.value})
        if self.fail:
            raise ModelGatewayError("forced failure")
        return json.dumps({"answer": "unused"}, ensure_ascii=False)

    def complete_structured(self, prompt: str, schema: type[Any], tier: ModelTier = ModelTier.FAST, fallback: Any | None = None) -> Any:
        self.calls.append({"prompt": prompt, "tier": tier.value, "schema": schema.__name__})
        if self.fail:
            if fallback is not None:
                return fallback
            raise ModelGatewayError("forced failure")
        value = self.outputs.get(schema)
        if isinstance(value, str):
            return schema.model_validate_json(value)
        if isinstance(value, dict):
            return schema.model_validate(value)
        if fallback is not None:
            return fallback
        raise ModelGatewayError(f"no output for {schema.__name__}")


def make_client_and_repo(tmp_path: Path, gateway: ModelGateway | None = None) -> tuple[TestClient, Repository]:
    database = Database(f"sqlite:///{tmp_path / 'learnos.sqlite3'}")
    database.init()
    app = create_app(database=database, model_gateway=gateway or FakeModelGateway())
    return TestClient(app), Repository(database)


def test_create_core_app_selects_openai_gateway_when_env_configured(tmp_path: Path, monkeypatch) -> None:
    database = Database(f"sqlite:///{tmp_path / 'gateway.sqlite3'}")
    database.init()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")

    app = create_core_app(database=database)

    assert isinstance(app.model_gateway, OpenAICompatibleGateway)


def valid_state_writer_payload(message: str = "CFT 和临界点有什么区别？") -> dict[str, Any]:
    return {
        "new_claims": [],
        "updated_claims": [],
        "new_distinctions": [
            {
                "concept_a": "CFT",
                "concept_b": "临界点",
                "boundary": "CFT is a possible continuum description, while a critical point is the learner's physical target.",
                "common_confusion": "Treating criticality and conformal description as identical.",
                "example": "A critical lattice model may require extra assumptions before a CFT description applies.",
                "test_question": "What extra condition would make the CFT description fail?",
            }
        ],
        "new_temporal_trace": {
            "event_type": "chat",
            "user_question": message,
            "system_response_summary": "Explained the distinction.",
            "state_change_summary": "Model proposed one grounded distinction.",
            "next_step": "Do a no-AI distinction check.",
        },
        "knowledge_position_updates": [],
        "derivation_trust_updates": [],
        "review_triggers": [],
        "next_recommended_action": "Do a no-AI distinction check.",
        "source_metadata": {"source_type": "user_question", "source_message_id": "msg_test", "evidence_text": message},
        "user_originated_updates": {"distinctions": 1, "temporal_traces": 1},
        "ai_only_observations": {"note": "not durable"},
        "discarded_ephemeral_judgments": {"model_state_writer": "validated"},
    }


def test_answer_composer_uses_strong_tier_and_model_answer(tmp_path: Path) -> None:
    gateway = SpyStructuredGateway(
        {
            AnswerComposerOutput: {
                "answer": "强模型回答：CFT 不是把每个临界点都自动命名为同一个东西。",
                "exercise": None,
                "follow_up_question": None,
                "suggested_next_action": "做一个边界辨析。",
            },
            StateWriterOutput: valid_state_writer_payload(),
        }
    )
    client, _ = make_client_and_repo(tmp_path, gateway)
    project = client.post("/api/projects", json={"name": "CFT"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "CFT 和临界点有什么区别？"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("强模型回答")
    assert any(call.get("schema") == "AnswerComposerOutput" and call["tier"] == "strong" for call in gateway.calls)
    assert any(call.get("schema") == "StateWriterOutput" and call["tier"] == "medium" for call in gateway.calls)


def test_model_gateway_failure_falls_back_to_deterministic_answer(tmp_path: Path) -> None:
    gateway = SpyStructuredGateway(fail=True)
    client, _ = make_client_and_repo(tmp_path, gateway)
    project = client.post("/api/projects", json={"name": "Fallback"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？"})

    assert response.status_code == 200
    assert response.json()["answer"]
    assert any(call.get("schema") == "AnswerComposerOutput" and call["tier"] == "strong" for call in gateway.calls)


def test_invalid_model_answer_falls_back_to_deterministic_answer(tmp_path: Path) -> None:
    gateway = SpyStructuredGateway({AnswerComposerOutput: {"answer": "missing required next action"}})
    client, _ = make_client_and_repo(tmp_path, gateway)
    project = client.post("/api/projects", json={"name": "Invalid Fallback"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "二阶相变处一定是 CFT 吗？"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("简要解释")
    assert any(call.get("schema") == "AnswerComposerOutput" and call["tier"] == "strong" for call in gateway.calls)


def test_model_state_writer_is_sanitized_for_greeting(tmp_path: Path) -> None:
    aggressive = valid_state_writer_payload("你好")
    aggressive["new_claims"] = [
        {
            "original_statement": "你好",
            "normalized_statement": "Greeting proves understanding",
            "related_concept": "greeting",
            "epistemic_status": "strict_fact",
            "confidence": 0.9,
            "correction": None,
        }
    ]
    aggressive["review_triggers"] = [
        {
            "target": "greeting",
            "trigger_reason": "too aggressive",
            "review_type": "explain",
            "scheduled_time": "2030-01-01T00:00:00Z",
            "success_criteria": "none",
        }
    ]
    gateway = SpyStructuredGateway({StateWriterOutput: aggressive})
    client, _ = make_client_and_repo(tmp_path, gateway)
    project = client.post("/api/projects", json={"name": "Sanitize"}).json()

    response = client.post("/api/chat", json={"project_id": project["id"], "message": "你好"})

    assert response.status_code == 200
    state = client.get(f"/api/projects/{project['id']}/state").json()
    assert len(state["temporal_traces"]) == 1
    assert state["claims"] == []
    assert state["review_triggers"] == []


def test_reference_chunks_are_in_context_pack_and_reused_by_unit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_LEARN_DEBUG_PERSIST_CONTEXT", "1")
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "CFT References"}).json()
    client.post(
        f"/api/projects/{project['id']}/references",
        json={
            "title": "CFT mini note",
            "source_type": "manual",
            "reliability_level": "high",
            "scope": "CFT learning seed",
            "text": "CFT describes scaling limits with conformal symmetry. Minimal models include Ising CFT and tricritical Ising CFT. " * 20,
        },
    )

    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "Ising CFT 和 tricritical Ising CFT 有什么区别？", "selected_mode": "compare"},
    ).json()

    persisted = repo.list_by_project("context_packs", project["id"])
    assert "Minimal models include Ising CFT" in persisted[0]["reference_context"]
    unit = repo.get_by_id("learning_units", first["active_learning_unit"]["id"])
    assert unit is not None
    assert "Minimal models include Ising CFT" in unit["context_snapshot_json"]["context_pack"]["reference_context"]

    second = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "继续这个比较", "selected_mode": "auto"},
    ).json()

    assert second["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is False
    assert "Reusing" not in second["pipeline_trace"]["steps"][3]["output"]["reference_context"]
    assert "Minimal models include Ising CFT" in second["pipeline_trace"]["steps"][3]["output"]["reference_context"]


def test_user_close_unit_runs_distillation_and_logs_it(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Close Unit"}).json()
    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "CFT 和临界点有什么区别？", "selected_mode": "compare"},
    ).json()

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "结束这个小单元，总结一下", "selected_mode": "auto"},
    )

    assert response.status_code == 200
    unit = repo.get_by_id("learning_units", first["active_learning_unit"]["id"])
    assert unit is not None
    assert unit["status"] == "closed"
    assert "CFT" in unit["unit_summary"]
    logs = repo.list_by_project("state_update_logs", project["id"], limit=10)
    payloads = [log["payload_json"] for log in logs]
    assert any(payload.get("source_metadata", {}).get("source_type") == "system_trace" and "unit_close" in payload.get("source_metadata", {}).get("evidence_text", "") for payload in payloads)


def test_run_next_refreshes_and_jumps_active_units(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Run Next Unit"}).json()
    chat = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "CFT 和临界点有什么区别？", "selected_mode": "compare"},
    ).json()
    unit_id = chat["active_learning_unit"]["id"]
    client.post(f"/api/projects/{project['id']}/learning-units/{unit_id}/refresh-context")

    refreshed = client.post("/api/run-next", json={"project_id": project["id"]}).json()
    assert refreshed["pipeline_trace"]["learning_unit"]["action"] == "refresh_active_unit"
    assert refreshed["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is True

    client.post(
        f"/api/projects/{project['id']}/review-triggers",
        json={
            "target": "CFT vs scale invariance",
            "trigger_reason": "due now",
            "review_type": "distinguish",
            "scheduled_time": "2000-01-01T00:00:00Z",
            "success_criteria": "Explain without AI.",
        },
    )
    jumped = client.post("/api/run-next", json={"project_id": project["id"]}).json()
    assert jumped["chosen_module"] == "review_point_runner"
    assert jumped["pipeline_trace"]["learning_unit"]["action"] == "jump_to_global_priority"


def test_seed_cft_learning_script_creates_focused_project(tmp_path: Path) -> None:
    from scripts.seed_cft_learning import seed_cft_learning

    database = Database(f"sqlite:///{tmp_path / 'seed.sqlite3'}")
    database.init()
    repo = Repository(database)

    project = seed_cft_learning(repository=repo)

    assert project["name"] == "我要学习 CFT"
    state = repo.project_state(project["id"])
    assert repo.list_goal_stacks(project["id"])[0]["main_goal"] == "我要学习 CFT"
    assert repo.list_references(project["id"])
    assert state["claims"]
    assert state["distinctions"]
    assert state["knowledge_positions"]
    assert state["review_triggers"]
    assert state["derivation_trust_records"]


def test_seeded_cft_project_chat_smoke_uses_chunks_and_selective_state(tmp_path: Path) -> None:
    from scripts.seed_cft_learning import seed_cft_learning

    database = Database(f"sqlite:///{tmp_path / 'cft-smoke.sqlite3'}")
    database.init()
    repo = Repository(database)
    project = seed_cft_learning(repository=repo)
    client = TestClient(create_app(database=database, model_gateway=FakeModelGateway()))

    response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "为什么 2D CFT 可以描述二阶临界点？", "selected_mode": "auto"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
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
    context_pack = data["pipeline_trace"]["steps"][3]["output"]
    assert "Excerpt:" in context_pack["reference_context"]
    assert "二维共形场论" in context_pack["reference_context"] or "Ising CFT" in context_pack["reference_context"]
    assert data["active_learning_unit"]["status"] == "active"
    assert len(data["state_updates"]["temporal_traces"]) == 1
    assert len(data["state_updates"]["claims"]) <= 1
    assert len(data["state_updates"]["distinctions"]) <= 1
    assert len(data["state_updates"]["review_triggers"]) <= 1
    assert data["state_updates"]["knowledge_positions"] == []
    assert data["state_updates"]["derivation_trust_records"] == []


def test_seeded_cft_learning_unit_continuity_and_close_distillation(tmp_path: Path) -> None:
    from scripts.seed_cft_learning import seed_cft_learning

    database = Database(f"sqlite:///{tmp_path / 'cft-unit.sqlite3'}")
    database.init()
    repo = Repository(database)
    project = seed_cft_learning(repository=repo)
    client = TestClient(create_app(database=database, model_gateway=FakeModelGateway()))

    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "CFT 和二阶临界点之间到底是什么关系？", "selected_mode": "socratic"},
    ).json()
    unit_id = first["active_learning_unit"]["id"]
    initial_unit = repo.get_by_id("learning_units", unit_id)
    assert initial_unit is not None
    assert initial_unit["context_snapshot_json"]["context_pack"]["reference_context"]

    second = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "那 scaling limit 到底是什么意思？", "selected_mode": "auto"},
    ).json()

    assert second["active_learning_unit"]["id"] == unit_id
    assert second["pipeline_trace"]["learning_unit"]["should_run_full_context_extraction"] is False
    assert len(repo.list_learning_unit_turns(unit_id)) == 4
    reused_unit = repo.get_by_id("learning_units", unit_id)
    assert reused_unit is not None
    assert reused_unit["context_snapshot_json"]["context_pack"]["reference_context"] == initial_unit["context_snapshot_json"]["context_pack"]["reference_context"]

    closed_response = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "结束这个小单元，总结一下。", "selected_mode": "auto"},
    ).json()

    assert closed_response["active_learning_unit"] is None
    closed = repo.get_by_id("learning_units", unit_id)
    assert closed is not None
    assert closed["status"] == "closed"
    assert "Learner-side evidence" in closed["unit_summary"]
    logs = repo.list_by_project("state_update_logs", project["id"], limit=20)
    close_payloads = [
        log["payload_json"]
        for log in logs
        if "unit_close" in log["payload_json"].get("source_metadata", {}).get("evidence_text", "")
    ]
    assert close_payloads
    created = close_payloads[0]["created"]
    assert len(created["claims"]) == 0
    assert len(created["distinctions"]) <= 1
    assert len(created["review_triggers"]) <= 1


def test_seeded_cft_run_next_smoke_with_active_unit(tmp_path: Path) -> None:
    from scripts.seed_cft_learning import seed_cft_learning

    database = Database(f"sqlite:///{tmp_path / 'cft-run-next.sqlite3'}")
    database.init()
    repo = Repository(database)
    project = seed_cft_learning(repository=repo)
    client = TestClient(create_app(database=database, model_gateway=FakeModelGateway()))

    first = client.post("/api/run-next", json={"project_id": project["id"]}).json()

    assert first["chosen_module"] in {"no_ai_reconstruction_tester", "auto_run_router", "review_point_runner"}
    assert first["priority"] in {"unverified_no_ai_internalization", "current_goal_next_action", "due_review_trigger"}
    assert first["loop_step"]
    assert first["why_this_now"]
    assert first["expected_user_action"]
    assert first["will_update"]
    assert first["active_learning_unit"]
    assert first["pipeline_trace"]["learning_unit"]["action"] == "create_new_unit"

    second = client.post("/api/run-next", json={"project_id": project["id"]}).json()

    assert second["chosen_module"]
    assert second["priority"]
    assert second["loop_step"]
    assert second["why_this_now"]
    assert second["expected_user_action"]
    assert second["will_update"]
    assert second["active_learning_unit"]
    assert second["pipeline_trace"]["learning_unit"]["action"] in {
        "continue_active_unit",
        "refresh_active_unit",
        "close_active_unit",
        "jump_to_global_priority",
        "create_new_unit",
    }

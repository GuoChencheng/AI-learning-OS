from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from ailearn.api.app import create_app
from ailearn.api.testing import TestClient
from ailearn.assessment.claim import ClaimEpistemicEvaluator
from ailearn.assessment.derivation import DerivationTrustEvaluator
from ailearn.assessment.distinction import DistinctionTestEvaluator
from ailearn.assessment.misconception import MisconceptionTracker
from ailearn.assessment.no_ai import NoAITestEvaluator
from ailearn.db.database import Database
from ailearn.db.repository import Repository, now_iso
from ailearn.model_gateway.fake import FakeModelGateway


def make_repo(tmp_path: Path) -> Repository:
    database = Database(f"sqlite:///{tmp_path / 'assessment.sqlite3'}")
    database.init()
    return Repository(database)


def make_client_and_repo(tmp_path: Path) -> tuple[TestClient, Repository]:
    database = Database(f"sqlite:///{tmp_path / 'assessment-api.sqlite3'}")
    database.init()
    app = create_app(database=database, model_gateway=FakeModelGateway())
    return TestClient(app), Repository(database)


def test_no_ai_assessment_scores_a0_to_a3_but_not_fresh_a4(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "CFT"})
    position = repo.update_knowledge_position_assessment(
        project["id"],
        "CFT 与临界点的边界",
        previous_level="A0",
        new_level="A0",
        result="failed",
        evidence_text="seed",
        reason="initial target",
    )

    weak = NoAITestEvaluator().evaluate(project["id"], "CFT 与临界点的边界", "CFT 就是临界点附近的理论。", position, {}, FakeModelGateway())
    assert weak.new_level == "A1"
    assert weak.result == "partial"

    boundary = NoAITestEvaluator().evaluate(
        project["id"],
        "CFT 与临界点的边界",
        "二阶临界点需要先取 scaling limit；CFT 是满足共形对称等额外条件后的描述，不是每个临界点都一定成立，反例如长程相互作用。",
        position,
        {},
        FakeModelGateway(),
    )
    assert boundary.new_level == "A2"
    assert boundary.should_schedule_review is True

    applied = NoAITestEvaluator().evaluate(
        project["id"],
        "CFT 与临界点的边界",
        "我可以用二维 Ising 模型说明：临界点取连续极限后由 Ising CFT 描述，并能解释为什么 tricritical Ising 属于不同 universality class。",
        position,
        {},
        FakeModelGateway(),
    )
    assert applied.new_level == "A3"
    assert applied.new_level != "A4"


def test_derivation_assessment_updates_done_hinted_and_untrusted_steps(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "Derive"})
    record = repo.add_derivation_trust_record(
        project["id"],
        {
            "result_or_tool": "有限大小标度读出 central charge",
            "assumptions": ["二维临界系统", "周期边界条件"],
            "key_steps": ["写出有限大小能谱修正", "识别 central charge 项"],
            "done_by_user": [],
            "hinted_by_ai": ["AI 提示了 central charge 项"],
            "untrusted_steps": [],
            "failure_conditions": ["漏掉边界条件"],
            "no_ai_reconstruction_status": "not_started",
        },
    )

    partial = DerivationTrustEvaluator().evaluate_step(project["id"], record["id"], "我能写出有限大小能谱修正，但边界条件我还没说明。", FakeModelGateway(), repo)
    assert "写出有限大小能谱修正" in partial.done_by_user
    assert partial.should_schedule_rederive is True
    updated = repo.get_by_id("derivation_trust_records", record["id"])
    assert updated is not None
    assert "写出有限大小能谱修正" in updated["done_by_user"]
    assert updated["untrusted_steps"]


def test_distinction_test_marks_clear_partial_or_failed_and_tracks_confusion(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "Distinguish"})
    distinction = repo.add_distinction(
        project["id"],
        {
            "concept_a": "CFT fusion",
            "concept_b": "anyon fusion",
            "boundary": "CFT fusion is an operator algebra datum; anyon fusion is topological superselection fusion.",
            "common_confusion": "Treating analogy as identity.",
            "example": "Related modular tensor category data can connect them, but they are not literally the same object.",
            "test_question": "Give a boundary and counterexample.",
        },
    )

    vague = DistinctionTestEvaluator().evaluate(project["id"], distinction["id"], "它们有关，但是有点不一样。", FakeModelGateway(), repo)
    assert vague.status == "partially_clear"

    failed = DistinctionTestEvaluator().evaluate(project["id"], distinction["id"], "CFT fusion 就是 anyon fusion，完全一样。", FakeModelGateway(), repo)
    assert failed.status == "failed"
    after_fail = repo.get_by_id("distinctions", distinction["id"])
    assert after_fail is not None
    assert after_fail["confusion_count"] == 1

    clear = DistinctionTestEvaluator().evaluate(
        project["id"],
        distinction["id"],
        "它们不是完全一样。CFT fusion 是 OPE/表示范畴里的代数规则；anyon fusion 是拓扑相中任意子类型融合。可以类比，但需要额外结构连接。",
        FakeModelGateway(),
        repo,
    )
    assert clear.status == "clear"


def test_claim_epistemic_assessment_and_updated_claims_persist(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "Claims"})
    created = repo.apply_state_writer_output(
        project["id"],
        None,
        {
            "new_claims": [
                {
                    "original_statement": "CFT fusion is exactly anyon fusion",
                    "normalized_statement": "CFT fusion is exactly anyon fusion",
                    "related_concept": "fusion",
                    "epistemic_status": "speculation",
                    "confidence": 0.4,
                    "correction": None,
                }
            ],
            "updated_claims": [],
            "new_distinctions": [],
            "new_temporal_trace": {
                "event_type": "test",
                "user_question": "seed",
                "system_response_summary": "seed",
                "state_change_summary": "seed",
                "next_step": "seed",
            },
            "knowledge_position_updates": [],
            "derivation_trust_updates": [],
            "review_triggers": [],
            "source_metadata": {"source_type": "user_explicit", "source_message_id": None, "evidence_text": "seed"},
        },
    )["claims"][0]

    exact = ClaimEpistemicEvaluator().evaluate(project["id"], created, "CFT fusion is exactly anyon fusion", None, FakeModelGateway())
    assert exact.epistemic_status == "wrong"
    assert exact.status in {"wrong", "misleading"}

    analogy = ClaimEpistemicEvaluator().evaluate(project["id"], created, "CFT fusion resembles anyon fusion in some modular tensor category examples", None, FakeModelGateway())
    assert analogy.epistemic_status in {"analogy", "inference"}
    assert analogy.caveat

    strategy = ClaimEpistemicEvaluator().evaluate(project["id"], created, "Ising CFT is a good first example to learn", None, FakeModelGateway())
    assert strategy.epistemic_status == "learning_strategy"

    repo.apply_state_writer_output(
        project["id"],
        None,
        {
            "new_claims": [],
            "updated_claims": [exact.model_dump(mode="json")],
            "new_distinctions": [],
            "new_temporal_trace": {
                "event_type": "claim_assessment",
                "user_question": exact.original_statement,
                "system_response_summary": exact.reason,
                "state_change_summary": "updated claim epistemic status",
                "next_step": "repair the misconception",
            },
            "knowledge_position_updates": [],
            "derivation_trust_updates": [],
            "review_triggers": [],
            "source_metadata": {"source_type": "user_explicit", "source_message_id": None, "evidence_text": exact.evidence_text},
        },
    )
    updated = repo.get_by_id("claims", created["id"])
    assert updated is not None
    assert updated["epistemic_status"] == "wrong"
    assert updated["status"] == exact.status


def test_misconception_recurrence_and_learning_summary(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "Misconception"})

    first = MisconceptionTracker().record_or_update(
        project["id"],
        "CFT fusion 就是 anyon fusion",
        [],
        [],
        "first answer",
        repo,
    )
    second = MisconceptionTracker().record_or_update(
        project["id"],
        "CFT fusion exactly equals anyon fusion",
        [],
        [],
        "second answer",
        repo,
    )

    assert first["misconception_key"] == second["misconception_key"]
    assert second["recurrence_count"] == 2
    assert second["status"] == "recurring"
    summary = repo.project_learning_summary(project["id"])
    assert summary["current_blocker"]["type"] == "misconception"
    assert summary["counts"]["recurring_misconceptions"] == 1


def test_review_trigger_complete_fail_skip_and_run_next_priority(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "Review"}).json()
    due_time = (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    trigger = repo.create_review_trigger(
        project["id"],
        {
            "target": "CFT boundary",
            "trigger_reason": "due review",
            "review_type": "distinguish",
            "scheduled_time": due_time,
            "success_criteria": "answer without AI",
        },
    )

    completed = client.post(f"/api/review-triggers/{trigger['id']}/complete", json={"evidence_text": "clear no-AI answer"}).json()
    assert completed["status"] == "completed"
    assert client.post("/api/run-next", json={"project_id": project["id"]}).json()["priority"] != "due_review_trigger"

    failed = repo.create_review_trigger(
        project["id"],
        {
            "target": "CFT fusion vs anyon fusion",
            "trigger_reason": "failed distinction",
            "review_type": "distinguish",
            "scheduled_time": due_time,
            "success_criteria": "state boundary",
        },
    )
    failed_response = client.post(f"/api/review-triggers/{failed['id']}/fail", json={"evidence_text": "collapsed concepts", "failure_reason": "equivalence error"}).json()
    assert failed_response["status"] == "failed"
    run_next = client.post("/api/run-next", json={"project_id": project["id"]}).json()
    assert run_next["priority"] == "due_review_trigger"

    skipped = repo.create_review_trigger(
        project["id"],
        {
            "target": "optional review",
            "trigger_reason": "not needed now",
            "review_type": "explain",
            "scheduled_time": due_time,
            "success_criteria": "none",
        },
    )
    skipped_response = client.post(f"/api/review-triggers/{skipped['id']}/skip", json={"evidence_text": "learner skipped"}).json()
    assert skipped_response["status"] == "skipped"


def test_learning_summary_prioritizes_due_review_then_no_ai_gap(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    project = repo.create_project({"name": "Summary"})
    repo.update_knowledge_position_assessment(
        project["id"],
        "CFT 与临界点的边界",
        previous_level="A0",
        new_level="A1",
        result="partial",
        evidence_text="rough definition only",
        reason="below target",
    )

    summary = repo.project_learning_summary(project["id"])
    assert summary["current_blocker"]["type"] == "no_ai"
    assert summary["primary_next_action"]["module"] == "no_ai_reconstruction_tester"
    assert summary["counts"]["no_ai_below_A3"] == 1

    repo.create_review_trigger(
        project["id"],
        {
            "target": "urgent review",
            "trigger_reason": "due",
            "review_type": "explain",
            "scheduled_time": "2000-01-01T00:00:00Z",
            "success_criteria": "answer",
        },
    )
    due_summary = repo.project_learning_summary(project["id"])
    assert due_summary["current_blocker"]["type"] == "review"
    assert due_summary["primary_next_action"]["module"] == "review_point_runner"


def test_chat_assessment_tracks_repeated_cft_misconception_and_summary_endpoint(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "我要学习 CFT"}).json()

    first = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "CFT fusion 就是 anyon fusion 吗？", "selected_mode": "auto", "button_action": None},
    ).json()
    second = client.post(
        "/api/chat",
        json={"project_id": project["id"], "message": "CFT fusion exactly equals anyon fusion?", "selected_mode": "auto", "button_action": None},
    ).json()

    assert first["answer"]
    assert second["pipeline_trace"]["assessment"]["misconception"]["status"] == "recurring"
    records = repo.project_state(project["id"])["misconception_records"]
    assert records[0]["recurrence_count"] == 2

    summary = client.get(f"/api/projects/{project['id']}/learning-summary").json()
    assert summary["current_blocker"]["type"] == "misconception"
    assert summary["primary_next_action"]["module"] == "flawed_interpretation_critic"


def test_run_next_prioritizes_recurring_misconception_records(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "RunNext Misconception"}).json()
    MisconceptionTracker().record_or_update(
        project["id"],
        "CFT fusion 就是 anyon fusion",
        [],
        [],
        "first collapse",
        repo,
    )
    MisconceptionTracker().record_or_update(
        project["id"],
        "CFT fusion exactly equals anyon fusion",
        [],
        [],
        "second collapse",
        repo,
    )

    response = client.post("/api/run-next", json={"project_id": project["id"]})

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "repeated_misconception"
    assert data["chosen_module"] == "flawed_interpretation_critic"
    assert "CFT fusion" in data["reason"] or "cft_fusion_equals_anyon_fusion" in data["reason"]


def test_chat_no_ai_button_updates_knowledge_position_assessment(tmp_path: Path) -> None:
    client, repo = make_client_and_repo(tmp_path)
    project = client.post("/api/projects", json={"name": "No AI"}).json()

    response = client.post(
        "/api/chat",
        json={
            "project_id": project["id"],
            "message": "我可以用二维 Ising 模型说明 scaling limit 后由 Ising CFT 描述。",
            "selected_mode": "auto",
            "button_action": "no_ai_test",
        },
    ).json()

    assert response["state_updates"]["assessments"]["no_ai"]["new_level"] == "A3"
    positions = repo.project_state(project["id"])["knowledge_positions"]
    assert any(item["last_assessment_result"] == "passed" and item["current_level"] == "A3" for item in positions)

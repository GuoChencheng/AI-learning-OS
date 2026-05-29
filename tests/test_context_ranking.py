from __future__ import annotations

from ailearn.context_ranking import extract_keywords, rank_records, score_record


def test_extract_keywords_handles_english_and_chinese_learning_terms() -> None:
    keywords = extract_keywords("二阶相变处一定是 CFT 吗？critical point and conformal symmetry")

    assert "cft" in keywords
    assert "critical" in keywords
    assert "二阶相变" in keywords
    assert "一定是" in keywords


def test_context_ranking_prioritizes_relevant_pending_learning_state() -> None:
    request = "二阶相变处一定是 CFT 吗？"
    records = [
        {
            "id": "old",
            "original_statement": "Unrelated old note about Fourier transforms",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "deprecated",
            "original_statement": "CFT appears in many critical phenomena examples.",
            "status": "deprecated",
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "cft-claim",
            "original_statement": "I think every second-order phase transition is CFT.",
            "related_concept": "CFT",
            "epistemic_status": "open_question",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
        },
    ]

    ranked = rank_records(records, request, "claim", limit=3)

    assert ranked[0]["id"] == "cft-claim"
    assert ranked[-1]["id"] == "deprecated"


def test_review_trigger_ranking_prefers_pending_due_cft_trigger() -> None:
    request = "二阶相变处一定是 CFT 吗？"
    records = [
        {
            "id": "completed",
            "target": "CFT description",
            "trigger_reason": "old check",
            "status": "completed",
            "scheduled_time": "2000-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "pending-cft",
            "target": "CFT description",
            "trigger_reason": "boundary still unclear",
            "status": "pending",
            "scheduled_time": "2000-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        },
    ]

    ranked = rank_records(records, request, "review_trigger", limit=2)

    assert ranked[0]["id"] == "pending-cft"
    assert score_record(ranked[0], request, "review_trigger") > score_record(ranked[1], request, "review_trigger")

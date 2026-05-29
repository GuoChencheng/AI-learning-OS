from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta

from ailearn.db.repository import Repository


class MisconceptionTracker:
    def record_or_update(
        self,
        project_id: str,
        statement: str,
        related_claim_ids: list[str],
        related_distinction_ids: list[str],
        evidence_text: str,
        repository: Repository,
    ) -> dict:
        key = misconception_key(statement)
        next_action = _next_action_for_key(key)
        record = repository.upsert_misconception_record(
            project_id,
            key,
            statement,
            related_claim_ids,
            related_distinction_ids,
            evidence_text,
            next_action,
            severity="high" if key != _fallback_key(statement) else "medium",
        )
        repository.log_assessment_update(
            project_id,
            None,
            "misconception_recurrence",
            {
                "misconception_id": record["id"],
                "misconception_key": key,
                "recurrence_count": record.get("recurrence_count", 1),
                "source_metadata": {"source_type": "user_error", "evidence_text": evidence_text[:500]},
            },
        )
        if int(record.get("recurrence_count") or 1) >= 2:
            _ensure_review_trigger(project_id, record, repository)
        return record


def misconception_key(statement: str) -> str:
    text = _normalize(statement)
    if "critical" in text and "cft" in text and any(marker in text for marker in ("equals", "exactly", "就是", "等同", "same")):
        return "critical_point_equals_cft"
    if "scale" in text and "conformal" in text and any(marker in text for marker in ("equals", "exactly", "就是", "等同", "same")):
        return "scale_equals_conformal"
    if "cft" in text and "fusion" in text and ("anyon" in text or "任意子" in text) and any(marker in text for marker in ("equals", "exactly", "就是", "等同", "same")):
        return "cft_fusion_equals_anyon_fusion"
    if (("primary" in text and "descendant" in text) or ("主场" in text and "后代" in text)) and any(marker in text for marker in ("equals", "same", "就是", "等同", "完全一样")):
        return "primary_equals_descendant"
    if "fusion rule" in text and "ope" in text:
        return "fusion_rule_equals_full_ope"
    if ("ai" in text or "解释" in text) and any(marker in text for marker in ("understanding", "学会", "懂了", "learned")):
        return "ai_explanation_equals_understanding"
    return _fallback_key(statement)


def _ensure_review_trigger(project_id: str, record: dict, repository: Repository) -> None:
    existing = [
        item for item in repository.project_state(project_id)["review_triggers"]
        if item.get("target") == record["statement"] and item.get("status") == "pending"
    ]
    if existing:
        return
    repository.create_review_trigger(
        project_id,
        {
            "target": record["statement"],
            "trigger_reason": f"Recurring misconception: {record['misconception_key']}",
            "review_type": "error_check",
            "scheduled_time": _next_review_time(),
            "success_criteria": "Learner states the misconception, repairs it, and gives a distinction test.",
        },
    )


def _next_action_for_key(key: str) -> str:
    if key == "cft_fusion_equals_anyon_fusion":
        return "Run a flawed-interpretation critique and test the CFT fusion vs anyon fusion boundary."
    if key == "critical_point_equals_cft":
        return "Test the boundary between critical point, scaling limit, and CFT description."
    if key == "primary_equals_descendant":
        return "Retest primary vs descendant roles inside one conformal family."
    return "Turn the repeated wrong pattern into a distinction test."


def _normalize(statement: str) -> str:
    text = statement.strip().lower()
    return re.sub(r"\s+", " ", text)


def _fallback_key(statement: str) -> str:
    normalized = _normalize(statement)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"misc_{digest}"


def _next_review_time() -> str:
    return (datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)).isoformat().replace("+00:00", "Z")

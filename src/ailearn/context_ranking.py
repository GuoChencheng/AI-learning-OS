from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any


ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "why",
}

CHINESE_KEY_PHRASES = [
    "二阶相变",
    "临界点",
    "平均场",
    "临界指数",
    "无 AI",
    "不用 AI",
    "一定是",
    "是不是",
    "是否",
    "等同",
    "区别",
    "推导",
    "内化",
    "回看",
]


def extract_keywords(text: str) -> set[str]:
    lowered = text.lower()
    keywords = {word for word in re.findall(r"[a-z][a-z0-9_+-]{1,}", lowered) if word not in ENGLISH_STOPWORDS}
    keywords.update(phrase for phrase in CHINESE_KEY_PHRASES if phrase in text)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for run in chinese_runs:
        if len(run) <= 8:
            keywords.add(run)
        else:
            for phrase in CHINESE_KEY_PHRASES:
                if phrase in run:
                    keywords.add(phrase)
    return keywords


def score_record(record: dict[str, Any], request: str, kind: str) -> float:
    keywords = extract_keywords(request)
    searchable = _searchable_text(record)
    score = 0.0
    for keyword in keywords:
        if keyword and keyword.lower() in searchable:
            score += 3.0

    status = str(record.get("status") or record.get("epistemic_status") or "").lower()
    if status in {"active", "open", "open_question", "unverified", "revised", "pending"}:
        score += 4.0
    if status in {"deprecated", "skipped", "completed", "trusted"}:
        score -= 15.0

    if kind == "review_trigger":
        if record.get("status") == "pending":
            score += 6.0
        if _is_due(record.get("scheduled_time")):
            score += 8.0
    if kind == "knowledge_position":
        if record.get("layer") == "no_ai_internalization":
            score += 5.0
        if record.get("current_level") in {"A0", "A1", "A2"}:
            score += 4.0
    if kind == "derivation_trust":
        if record.get("untrusted_steps") or record.get("no_ai_reconstruction_status") not in {None, "", "trusted", "passed"}:
            score += 5.0
    if kind == "temporal_trace":
        score += _recency_bonus(record.get("created_at"))

    return score


def rank_records(records: list[dict[str, Any]], request: str, kind: str, limit: int) -> list[dict[str, Any]]:
    scored = [(score_record(record, request, kind), _timestamp(record), index, record) for index, record in enumerate(records)]
    scored.sort(key=lambda item: (item[0], item[1], -item[2]), reverse=True)
    return [record for _, _, _, record in scored[:limit]]


def _searchable_text(record: dict[str, Any]) -> str:
    values: list[str] = []
    for value in record.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            values.append(_searchable_text(value))
    return " ".join(values).lower()


def _is_due(value: Any) -> bool:
    parsed = _parse_time(value)
    return bool(parsed and parsed <= datetime.now(UTC))


def _recency_bonus(value: Any) -> float:
    parsed = _parse_time(value)
    if not parsed:
        return 0.0
    age_days = max((datetime.now(UTC) - parsed).days, 0)
    if age_days <= 2:
        return 4.0
    if age_days <= 14:
        return 2.0
    return 0.5


def _timestamp(record: dict[str, Any]) -> float:
    parsed = _parse_time(record.get("updated_at") or record.get("created_at") or record.get("scheduled_time"))
    return parsed.timestamp() if parsed else 0.0


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None

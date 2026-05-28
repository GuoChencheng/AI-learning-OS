from __future__ import annotations

from datetime import datetime, timedelta

from .ids import now_utc


def classify_temporal_state(
    *,
    first_seen_at: datetime | None = None,
    last_reviewed_at: datetime | None = None,
    last_checked_at: datetime | None = None,
    next_review_at: datetime | None = None,
    delayed_retrieval_failed: bool = False,
    recurrence_count: int = 0,
    review_interval_days: int = 14,
    now: datetime | None = None,
) -> str:
    current = now or now_utc()
    if delayed_retrieval_failed:
        return "forgetting_detected"
    if recurrence_count >= 2:
        return "persistent_misconception"
    if next_review_at is not None and next_review_at <= current:
        return "overdue"
    if last_reviewed_at is not None and current - last_reviewed_at >= timedelta(days=review_interval_days):
        return "review_due"
    if last_checked_at is not None and current - last_checked_at <= timedelta(days=3):
        return "recently_verified"
    if first_seen_at is not None and current - first_seen_at <= timedelta(days=3):
        return "new_or_provisional"
    if first_seen_at is not None and current - first_seen_at >= timedelta(days=30):
        return "stale"
    return "new_or_provisional"

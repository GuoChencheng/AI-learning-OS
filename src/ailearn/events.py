from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from .ids import new_id, now_utc

DEFAULT_TIMEZONE = "Asia/Shanghai"

EVENT_TYPES = {
    "record_created",
    "record_updated",
    "position_changed",
    "tool_role_changed",
    "internalization_level_changed",
    "claim_status_changed",
    "epistemic_status_changed",
    "derivation_status_changed",
    "test_status_changed",
    "distinction_status_changed",
    "confusion_recorded",
    "confusion_resolved",
    "delayed_retrieval_passed",
    "delayed_retrieval_failed",
    "review_scheduled",
    "review_completed",
    "revisit_trigger_added",
    "reference_added",
    "session_created",
}

EVENT_SOURCES = {"user", "system", "codex", "ai_prompt", "import"}

COMPACT_EVENT_FIELDS = {
    "id",
    "goal_id",
    "title",
    "topic",
    "knowledge_point",
    "text",
    "statement",
    "position",
    "tool_role",
    "status",
    "epistemic_status",
    "internalization_level",
    "internalization_target",
    "record_intensity",
    "confusion_count",
    "recurrence_count",
    "next_review_at",
    "next_retest_at",
    "next_rederive_at",
    "next_distinction_test_at",
    "next_action",
}


def compact_event_snapshot(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {key: value for key, value in data.items() if key in COMPACT_EVENT_FIELDS and value not in (None, "", [], {})}


class LearningEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp_utc: datetime
    timestamp_local: datetime
    timezone: str = DEFAULT_TIMEZONE
    event_type: str
    target_type: str
    target_id: str
    goal_id: str | None = None
    summary: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    reason: str | None = None
    source: str = "system"
    related_session_ids: list[str] = Field(default_factory=list)
    related_claim_ids: list[str] = Field(default_factory=list)
    related_position_ids: list[str] = Field(default_factory=list)
    related_derivation_ids: list[str] = Field(default_factory=list)

    @classmethod
    def new(
        cls,
        *,
        event_type: str,
        target_type: str,
        target_id: str,
        summary: str,
        goal_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str | None = None,
        source: str = "system",
        timezone: str = DEFAULT_TIMEZONE,
        related_session_ids: list[str] | None = None,
        related_claim_ids: list[str] | None = None,
        related_position_ids: list[str] | None = None,
        related_derivation_ids: list[str] | None = None,
    ) -> "LearningEvent":
        utc = now_utc()
        local = utc.astimezone(ZoneInfo(timezone))
        return cls(
            id=new_id("event"),
            timestamp_utc=utc,
            timestamp_local=local,
            timezone=timezone,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            goal_id=goal_id,
            summary=summary,
            before=before,
            after=after,
            reason=reason,
            source=source,
            related_session_ids=related_session_ids or [],
            related_claim_ids=related_claim_ids or [],
            related_position_ids=related_position_ids or [],
            related_derivation_ids=related_derivation_ids or [],
        )


def _event_dir(root: Path | str) -> Path:
    return Path(root) / "data" / "events"


def _month_path(root: Path | str, timestamp: datetime) -> Path:
    return _event_dir(root) / f"{timestamp.strftime('%Y-%m')}.jsonl"


def append_event(event: LearningEvent | dict[str, Any], root: Path | str = ".") -> LearningEvent:
    record = event if isinstance(event, LearningEvent) else LearningEvent.model_validate(event)
    if record.event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {record.event_type}")
    if record.source not in EVENT_SOURCES:
        raise ValueError(f"Invalid event source: {record.source}")
    path = _month_path(root, record.timestamp_utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
    return record


def load_events(month: str | None = None, root: Path | str = ".") -> list[LearningEvent]:
    event_dir = _event_dir(root)
    if not event_dir.exists():
        return []
    paths = [event_dir / f"{month}.jsonl"] if month else sorted(event_dir.glob("*.jsonl"))
    events: list[LearningEvent] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(LearningEvent.model_validate(json.loads(line)))
    return sorted(events, key=lambda event: event.timestamp_utc)


def load_events_for_target(target_id: str, root: Path | str = ".") -> list[LearningEvent]:
    return [event for event in load_events(root=root) if event.target_id == target_id]


def load_events_for_type(event_type: str, root: Path | str = ".") -> list[LearningEvent]:
    return [event for event in load_events(root=root) if event.event_type == event_type]


def build_timeline(record_id: str, root: Path | str = ".") -> list[str]:
    lines: list[str] = []
    for event in load_events_for_target(record_id, root=root):
        line = f"{event.timestamp_local.isoformat()} {event.event_type}: {event.summary}"
        if event.reason:
            line = f"{line} Reason: {event.reason}"
        lines.append(line)
    return lines


def summarize_events_for_record(record_id: str, root: Path | str = ".") -> str:
    timeline = build_timeline(record_id, root=root)
    if not timeline:
        return "No events recorded."
    return "\n".join(timeline)

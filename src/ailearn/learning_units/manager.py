from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ailearn.context_ranking import extract_keywords
from ailearn.modules.router import MODE_TO_MODULE


@dataclass(frozen=True)
class LearningUnitDecision:
    action: str
    unit_id: str | None
    reason: str
    should_run_full_context_extraction: bool
    method_override: str | None
    topic: str
    close_unit_id: str | None = None
    close_reason: str | None = None


class LearningUnitManager:
    def __init__(self, max_turns: int = 16) -> None:
        self.max_turns = max_turns

    def resolve_for_chat(
        self,
        project_id: str,
        user_message: str,
        selected_mode: str,
        button_action: str | None,
        repository: Any,
    ) -> LearningUnitDecision:
        active = repository.get_active_learning_unit(project_id)
        manual_method = _manual_method(selected_mode, button_action)
        topic = _topic_from_text(user_message)

        if active and _is_close_request(user_message):
            return LearningUnitDecision(
                action="no_unit",
                unit_id=active["id"],
                reason="User requested this learning unit to close.",
                should_run_full_context_extraction=False,
                method_override=active.get("method"),
                topic=active.get("topic") or topic,
                close_unit_id=active["id"],
                close_reason="user_requested_close",
            )

        if active and manual_method and manual_method != active.get("method"):
            return LearningUnitDecision(
                action="close_and_create_new",
                unit_id=None,
                reason="Manual method override conflicts with the active learning unit.",
                should_run_full_context_extraction=True,
                method_override=manual_method,
                topic=topic,
                close_unit_id=active["id"],
                close_reason="manual_method_switch",
            )

        if not active:
            return LearningUnitDecision(
                action="create_new_unit",
                unit_id=None,
                reason="No active learning unit exists.",
                should_run_full_context_extraction=True,
                method_override=manual_method,
                topic=topic,
            )

        snapshot = active.get("context_snapshot_json") if isinstance(active.get("context_snapshot_json"), dict) else {}
        if snapshot.get("refresh_requested"):
            return LearningUnitDecision(
                action="refresh_unit_context",
                unit_id=active["id"],
                reason="The active learning unit requested a context refresh.",
                should_run_full_context_extraction=True,
                method_override=manual_method or active.get("method"),
                topic=active.get("topic") or topic,
            )

        if int(active.get("turn_count") or 0) >= self.max_turns:
            return LearningUnitDecision(
                action="close_and_create_new",
                unit_id=None,
                reason="The active learning unit reached its turn limit.",
                should_run_full_context_extraction=True,
                method_override=manual_method or active.get("method"),
                topic=topic,
                close_unit_id=active["id"],
                close_reason="max_turns_reached",
            )

        if _topic_drift_high(active.get("topic", ""), user_message):
            return LearningUnitDecision(
                action="close_and_create_new",
                unit_id=None,
                reason="The request appears to start a new topic.",
                should_run_full_context_extraction=True,
                method_override=manual_method,
                topic=topic,
                close_unit_id=active["id"],
                close_reason="topic_drift",
            )

        return LearningUnitDecision(
            action="reuse_active_unit",
            unit_id=active["id"],
            reason="Active learning unit is still valid for this turn.",
            should_run_full_context_extraction=False,
            method_override=manual_method or active.get("method"),
            topic=active.get("topic") or topic,
        )


def _manual_method(selected_mode: str | None, button_action: str | None) -> str | None:
    key = button_action or (selected_mode if selected_mode and selected_mode != "auto" else None)
    if not key:
        return None
    return MODE_TO_MODULE.get(key, key if key in set(MODE_TO_MODULE.values()) else None)


def _is_close_request(message: str) -> bool:
    lowered = message.lower()
    return any(marker in message for marker in ("结束这个小单元", "结束小单元", "总结一下", "结束", "停止")) or any(
        marker in lowered for marker in ("finish this unit", "end this unit", "stop this unit", "close this unit")
    )


def _topic_drift_high(active_topic: str, message: str) -> bool:
    lowered = message.lower()
    if any(marker in lowered for marker in ("new topic", "switch topic")) or any(marker in message for marker in ("新话题", "换个话题", "切换到")):
        return True
    active_keywords = extract_keywords(active_topic)
    request_keywords = extract_keywords(message)
    if not active_keywords or not request_keywords:
        return False
    if any(marker in message for marker in ("这个", "这个条件", "那", "继续", "上面")):
        return False
    return active_keywords.isdisjoint(request_keywords) and len(active_keywords) >= 2 and len(request_keywords) >= 2


def _topic_from_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    return cleaned[:80].rstrip(" ?？。.") if cleaned else "current learning topic"

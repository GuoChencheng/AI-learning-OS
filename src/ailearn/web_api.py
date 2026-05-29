from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from pydantic import BaseModel

from .ai_runs import list_ai_runs, load_ai_run, preview_as_dict, preview_payload, save_ai_run_artifact
from .config import load_config, public_config_summary
from .context import build_context_pack, context_policy_text
from .events import LearningEvent, append_event, build_timeline, compact_event_snapshot, load_events, summarize_events_for_record
from .ids import new_id, now_utc
from .indexes import refresh_indexes, show_index, topic_summary
from .method_router import recommend_methods
from .models import (
    ClaimRecord,
    ClassificationPolicy,
    ConceptClusterRecord,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    SessionFootprint,
    TestRecord,
    VisualResourceRecord,
)
from .prompts import (
    claim_verification_prompt,
    classify_with_policy_prompt,
    deep_research_prompt,
    derivation_guidance_prompt,
    distinction_prompt,
    distinction_test_prompt,
    dynamic_positioning_prompt,
    extract_positioning_from_research_prompt,
    extract_references_prompt,
    goal_intake_prompt,
    method_router_prompt,
    misconception_correction_prompt,
    refine_policy_prompt,
    socratic_drill_prompt,
    temporal_review_prompt,
    test_record_prompt,
    test_topic_prompt,
    visual_explanation_prompt,
    visual_suggestion_prompt,
    weekly_review_prompt,
)
from .providers.base import ChatRequest
from .providers.registry import build_provider
from .review import generate_weekly_review
from .review import due_review_items
from .status import project_status, suggest_next_actions
from .storage import (
    active_goal,
    find_research_import,
    list_sessions,
    list_yaml_records,
    load_session,
    load_yaml_model,
    research_imports,
    save_session,
    save_yaml_model,
)
from .test_mode import suggest_tests
from .validate import validate_project


@dataclass
class ApiResponse:
    status: int
    data: dict[str, Any]


@dataclass(frozen=True)
class ResourceConfig:
    directory: str
    model: type[BaseModel]
    id_prefix: str


RESOURCES: dict[str, ResourceConfig] = {
    "goals": ResourceConfig("goals", Goal, "goal"),
    "positioning": ResourceConfig("positioning", PositionDecision, "pos"),
    "claims": ResourceConfig("claims", ClaimRecord, "claim"),
    "derivations": ResourceConfig("derivations", DerivationRecord, "der"),
    "references": ResourceConfig("references", ReferenceRecord, "ref"),
    "policies": ResourceConfig("policies", ClassificationPolicy, "policy"),
    "visuals": ResourceConfig("visuals", VisualResourceRecord, "visual"),
    "tests": ResourceConfig("tests", TestRecord, "test"),
    "distinctions": ResourceConfig("distinctions", DistinctionRecord, "dist"),
    "misconceptions": ResourceConfig("misconceptions", MisconceptionRecord, "misc"),
    "clusters": ResourceConfig("clusters", ConceptClusterRecord, "cluster"),
}


def model_to_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [model_to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: model_to_data(item) for key, item in value.items()}
    return value


def _ok(data: dict[str, Any], status: int = 200) -> ApiResponse:
    return ApiResponse(status, model_to_data(data))


def _error(message: str, status: int = 400) -> ApiResponse:
    return ApiResponse(status, {"error": message})


def _record_path(root: Path, config: ResourceConfig, record_id: str) -> Path:
    return root / "data" / config.directory / f"{record_id}.yaml"


def _load_resource(root: Path, resource: str, record_id: str) -> BaseModel:
    config = RESOURCES[resource]
    return load_yaml_model(_record_path(root, config, record_id), config.model)


def _save_resource(root: Path, resource: str, payload: dict[str, Any], record_id: str | None = None) -> BaseModel:
    config = RESOURCES[resource]
    now = now_utc()
    data = dict(payload)
    if record_id:
        existing = _load_resource(root, resource, record_id)
        before = existing.model_dump(mode="json")
        data = {**existing.model_dump(mode="json"), **data}
        data["id"] = record_id
        data["updated_at"] = now
    else:
        before = None
        data.setdefault("id", new_id(config.id_prefix))
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
    if resource != "goals" and not data.get("goal_id"):
        goal = active_goal(root)
        if goal is not None:
            data["goal_id"] = goal.id
    model = config.model.model_validate(data)
    save_yaml_model(_record_path(root, config, getattr(model, "id")), model)
    after = model.model_dump(mode="json")
    append_event(
        LearningEvent.new(
            event_type=_event_type_for_change(resource, before, after),
            target_type=resource,
            target_id=getattr(model, "id"),
            goal_id=getattr(model, "goal_id", None),
            summary=_event_summary(resource, before, after),
            before=compact_event_snapshot(before),
            after=compact_event_snapshot(after),
            source="system",
        ),
        root=root,
    )
    return model


def _event_type_for_change(resource: str, before: dict[str, Any] | None, after: dict[str, Any]) -> str:
    if before is None:
        if resource == "references":
            return "reference_added"
        return "record_created"
    changed = {key for key, value in after.items() if before.get(key) != value}
    if resource == "positioning" and "position" in changed:
        return "position_changed"
    if resource == "positioning" and "tool_role" in changed:
        return "tool_role_changed"
    if resource == "positioning" and "internalization_level" in changed:
        return "internalization_level_changed"
    if resource == "claims" and "status" in changed:
        return "claim_status_changed"
    if resource == "claims" and "epistemic_status" in changed:
        return "epistemic_status_changed"
    if resource == "derivations" and "status" in changed:
        return "derivation_status_changed"
    if resource == "tests" and "status" in changed:
        return "test_status_changed"
    if resource == "distinctions" and "status" in changed:
        return "distinction_status_changed"
    return "record_updated"


def _event_summary(resource: str, before: dict[str, Any] | None, after: dict[str, Any]) -> str:
    label = after.get("title") or after.get("topic") or after.get("knowledge_point") or after.get("text") or after.get("statement") or after.get("id")
    if before is None:
        return f"Created {resource} record: {label}"
    return f"Updated {resource} record: {label}"


def _apply_filters(items: list[BaseModel], query: dict[str, list[str]]) -> list[BaseModel]:
    filtered = items
    for key in [
        "goal_id",
        "position",
        "internalization_level",
        "record_intensity",
        "status",
        "epistemic_status",
        "reading_status",
        "topic",
        "severity",
    ]:
        values = query.get(key)
        if values:
            expected = values[0]
            filtered = [
                item
                for item in filtered
                if str(getattr(item, key, "")) == expected
                or (isinstance(getattr(item, "topics", None), list) and expected in getattr(item, "topics"))
            ]
    return filtered


def _list_resource(root: Path, resource: str, query: dict[str, list[str]]) -> ApiResponse:
    config = RESOURCES[resource]
    items = list_yaml_records(root, config.directory, config.model)
    return _ok({"items": _apply_filters(items, query)})


def _set_active_goal(root: Path, goal_id: str) -> ApiResponse:
    goals = list_yaml_records(root, "goals", Goal)
    target: Goal | None = None
    for goal in goals:
        data = goal.model_dump()
        data["active"] = goal.id == goal_id
        data["updated_at"] = now_utc()
        updated = Goal.model_validate(data)
        save_yaml_model(root / "data" / "goals" / f"{updated.id}.yaml", updated)
        if updated.id == goal_id:
            target = updated
    if target is None:
        return _error(f"Goal not found: {goal_id}", 404)
    return _ok({"item": target})


def _session_to_item(path: Path, session: SessionFootprint, body: dict[str, str]) -> dict[str, Any]:
    item = session.model_dump(mode="json")
    item["body"] = body
    item["path"] = str(path)
    return item


def _list_sessions(root: Path) -> ApiResponse:
    return _ok({"items": [_session_to_item(path, session, body) for path, session, body in list_sessions(root)]})


def _show_session(root: Path, session_id: str) -> ApiResponse:
    path = root / "data" / "sessions" / f"{session_id}.md"
    if not path.exists():
        return _error(f"Session not found: {session_id}", 404)
    session, body = load_session(path)
    return _ok({"item": _session_to_item(path, session, body), "markdown": path.read_text(encoding="utf-8")})


def _save_session_resource(root: Path, payload: dict[str, Any], session_id: str | None = None) -> ApiResponse:
    now = now_utc()
    body = payload.pop("body", None) or {}
    if session_id:
        path = root / "data" / "sessions" / f"{session_id}.md"
        existing, existing_body = load_session(path)
        data = {**existing.model_dump(mode="json"), **payload, "id": session_id}
        body = {**existing_body, **body}
    else:
        data = dict(payload)
        data.setdefault("id", new_id("session"))
        data.setdefault("created_at", now)
    if not data.get("goal_id"):
        goal = active_goal(root)
        if goal is not None:
            data["goal_id"] = goal.id
    session = SessionFootprint.model_validate(data)
    path = root / "data" / "sessions" / f"{session.id}.md"
    save_session(path, session, body)
    append_event(
        LearningEvent.new(
            event_type="session_created" if session_id is None else "record_updated",
            target_type="sessions",
            target_id=session.id,
            goal_id=session.goal_id,
            summary=f"{'Created' if session_id is None else 'Updated'} session: {session.topic}",
            source="system",
            related_session_ids=[session.id],
        ),
        root=root,
    )
    return _ok({"item": _session_to_item(path, session, body)}, 201 if session_id is None else 200)


def _list_reviews(root: Path) -> ApiResponse:
    items = []
    for path in sorted((root / "data" / "reviews").glob("*.md"), reverse=True):
        items.append({"id": path.stem, "path": str(path), "name": path.name, "markdown": path.read_text(encoding="utf-8")})
    return _ok({"items": items})


def _show_review(root: Path, review_id: str) -> ApiResponse:
    for path in sorted((root / "data" / "reviews").glob("*.md")):
        if review_id in {path.stem, path.name}:
            return _ok({"item": {"id": path.stem, "path": str(path), "name": path.name, "markdown": path.read_text(encoding="utf-8")}})
    return _error(f"Review not found: {review_id}", 404)


def _list_research_imports(root: Path) -> ApiResponse:
    return _ok(
        {
            "items": [
                {"id": path.stem, "name": path.name, "path": str(path), "markdown": path.read_text(encoding="utf-8")}
                for path in research_imports(root)
            ]
        }
    )


IMPORTANT_ACTIVITY_TYPES = {
    "claim_status_changed",
    "epistemic_status_changed",
    "derivation_status_changed",
    "test_status_changed",
    "internalization_level_changed",
    "confusion_recorded",
    "confusion_resolved",
    "review_scheduled",
    "review_completed",
    "reference_added",
    "delayed_retrieval_passed",
    "delayed_retrieval_failed",
}


def _active_goal_id(root: Path) -> str | None:
    goal = active_goal(root)
    return goal.id if goal else None


def _filter_goal(items: list[Any], goal_id: str | None) -> list[Any]:
    if goal_id is None:
        return items
    return [item for item in items if getattr(item, "goal_id", goal_id) == goal_id]


def _next_action_view(
    *,
    action_id: str,
    title: str,
    reason: str,
    priority: int,
    action_type: str,
    related_record_ids: list[str],
    suggested_prompt_type: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "title": title,
        "reason": reason,
        "priority": priority,
        "action_type": action_type,
        "related_record_ids": related_record_ids,
        "suggested_prompt_type": suggested_prompt_type,
        "due_date": due_date,
    }


def _dashboard_next_actions(
    root: Path,
    claims: list[ClaimRecord],
    derivations: list[DerivationRecord],
    positions: list[PositionDecision],
    distinctions: list[DistinctionRecord],
    misconceptions: list[MisconceptionRecord],
    tests: list[TestRecord],
    references: list[ReferenceRecord],
    goal: Goal | None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for claim in claims:
        if claim.status in {"unverified", "open_question"} and claim.record_intensity in {"medium", "heavy"}:
            actions.append(
                _next_action_view(
                    action_id=f"verify-{claim.id}",
                    title=f"Verify claim: {claim.text[:80]}",
                    reason=f"Status is {claim.status}; epistemic status is {claim.epistemic_status}.",
                    priority=10,
                    action_type="verify_claim",
                    related_record_ids=[claim.id],
                    suggested_prompt_type="claim-verification",
                )
            )
    for claim in claims:
        if claim.status in {"unverified", "open_question"} and not any(claim.id in action["related_record_ids"] for action in actions):
            actions.append(
                _next_action_view(
                    action_id=f"verify-{claim.id}",
                    title=f"Verify claim: {claim.text[:80]}",
                    reason="Learner-generated claim is not verified.",
                    priority=20,
                    action_type="verify_claim",
                    related_record_ids=[claim.id],
                    suggested_prompt_type="claim-verification",
                )
            )

    for derivation in derivations:
        if derivation.status != "trusted":
            actions.append(
                _next_action_view(
                    action_id=f"rederive-{derivation.id}",
                    title=f"Rebuild trust: {derivation.topic}",
                    reason=f"Derivation status is {derivation.status}; result to trust is recorded.",
                    priority=30,
                    action_type="rederive",
                    related_record_ids=[derivation.id],
                    suggested_prompt_type="derivation-guidance",
                    due_date=derivation.next_rederive_at.isoformat() if derivation.next_rederive_at else None,
                )
            )

    for test in tests:
        if test.status in {"planned", "failed", "needs_retest"}:
            actions.append(
                _next_action_view(
                    action_id=f"test-{test.id}",
                    title=f"Run test mode: {test.topic}",
                    reason=f"Test is {test.status}; target internalization is {test.internalization_target}.",
                    priority=40,
                    action_type="test_topic",
                    related_record_ids=[test.id],
                    suggested_prompt_type="test-record",
                    due_date=test.next_retest_at.isoformat() if test.next_retest_at else None,
                )
            )

    for position in positions:
        if position.internalization_level in {"A0", "A1"}:
            actions.append(
                _next_action_view(
                    action_id=f"internalize-{position.id}",
                    title=f"Test internalization: {position.knowledge_point}",
                    reason=f"{position.knowledge_point} is {position.position} at {position.internalization_level}.",
                    priority=45,
                    action_type="test_topic",
                    related_record_ids=[position.id],
                    suggested_prompt_type="test-topic",
                )
            )

    for distinction in distinctions:
        if distinction.status in {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}:
            actions.append(
                _next_action_view(
                    action_id=f"distinguish-{distinction.id}",
                    title=f"Resolve confusion: {distinction.title}",
                    reason=f"Distinction status is {distinction.status}; confusion count is {distinction.confusion_count}.",
                    priority=50,
                    action_type="resolve_confusion",
                    related_record_ids=[distinction.id],
                    suggested_prompt_type="distinction-test",
                    due_date=distinction.next_distinction_test_at.isoformat() if distinction.next_distinction_test_at else None,
                )
            )

    for misconception in misconceptions:
        if misconception.status in {"active", "recurring"} or misconception.recurrence_count >= 2:
            actions.append(
                _next_action_view(
                    action_id=f"misconception-{misconception.id}",
                    title=f"Correct misconception: {misconception.statement[:80]}",
                    reason=f"Misconception status is {misconception.status}; recurrence count is {misconception.recurrence_count}.",
                    priority=55,
                    action_type="resolve_confusion",
                    related_record_ids=[misconception.id],
                    suggested_prompt_type="misconception-correction",
                )
            )

    due = due_review_items(root)
    for index, item in enumerate(due[:5], start=1):
        actions.append(
            _next_action_view(
                action_id=f"review-due-{index}",
                title=f"Review due: {item.split(':', 1)[-1].strip()}",
                reason="A review, retest, distinction test, or rederive date is due.",
                priority=60 + index,
                action_type="review_due",
                related_record_ids=[item.split(":", 1)[0]],
                suggested_prompt_type="weekly-review",
            )
        )

    for reference in references:
        if reference.usage_stage == "core_learning" and reference.reading_status == "unread":
            actions.append(
                _next_action_view(
                    action_id=f"reference-{reference.id}",
                    title=f"Read or triage reference: {reference.title}",
                    reason="Core-learning reference is still unread.",
                    priority=70,
                    action_type="add_reference",
                    related_record_ids=[reference.id],
                    suggested_prompt_type="reference_review",
                )
            )

    if goal is None or not all([goal.main_goal, goal.stage_goal, goal.transfer_goal, goal.external_goal]):
        actions.append(
            _next_action_view(
                action_id="refine-goal",
                title="Refine the active goal",
                reason="The goal stack is incomplete or no active goal is selected.",
                priority=90,
                action_type="refine_goal",
                related_record_ids=[goal.id] if goal else [],
                suggested_prompt_type="goal-intake",
            )
        )

    return sorted(actions, key=lambda action: (action["priority"], action["id"]))


def _learning_item_view(record: Any, source_type: str) -> dict[str, Any]:
    title = (
        getattr(record, "knowledge_point", None)
        or getattr(record, "title", None)
        or getattr(record, "statement", None)
        or getattr(record, "topic", None)
        or getattr(record, "id")
    )
    status = getattr(record, "status", None) or getattr(record, "position", None)
    next_action = getattr(record, "next_action", "") or getattr(record, "reason", "")
    due = None
    for field in ["next_review_at", "next_retest_at", "next_rederive_at", "next_distinction_test_at"]:
        value = getattr(record, field, None)
        if value:
            due = value.isoformat()
            break
    return {
        "id": getattr(record, "id"),
        "source_type": source_type,
        "title": title,
        "status": str(status or ""),
        "position": str(getattr(record, "position", "") or ""),
        "internalization_level": str(getattr(record, "internalization_level", getattr(record, "internalization_target", "")) or ""),
        "record_intensity": str(getattr(record, "record_intensity", "") or "light"),
        "temporal_status": "due" if due else "",
        "due_date": due,
        "next_action": next_action,
        "updated_at": getattr(record, "updated_at", getattr(record, "created_at", "")).isoformat(),
        "source": model_to_data(record),
    }


def _learning_items(root: Path) -> list[dict[str, Any]]:
    goal_id = _active_goal_id(root)
    positions = _filter_goal(list_yaml_records(root, "positioning", PositionDecision), goal_id)
    distinctions = _filter_goal(list_yaml_records(root, "distinctions", DistinctionRecord), goal_id)
    misconceptions = _filter_goal(list_yaml_records(root, "misconceptions", MisconceptionRecord), goal_id)
    derivations = _filter_goal(list_yaml_records(root, "derivations", DerivationRecord), goal_id)
    tests = _filter_goal(list_yaml_records(root, "tests", TestRecord), goal_id)

    items = [
        *[_learning_item_view(record, "position") for record in positions],
        *[_learning_item_view(record, "distinction") for record in distinctions],
        *[_learning_item_view(record, "misconception") for record in misconceptions],
        *[_learning_item_view(record, "derivation") for record in derivations],
        *[_learning_item_view(record, "test") for record in tests],
    ]
    return sorted(items, key=lambda item: item["updated_at"], reverse=True)


def _dashboard_view(root: Path) -> dict[str, Any]:
    goal = active_goal(root)
    goal_id = goal.id if goal else None
    claims = _filter_goal(list_yaml_records(root, "claims", ClaimRecord), goal_id)
    derivations = _filter_goal(list_yaml_records(root, "derivations", DerivationRecord), goal_id)
    positions = _filter_goal(list_yaml_records(root, "positioning", PositionDecision), goal_id)
    distinctions = _filter_goal(list_yaml_records(root, "distinctions", DistinctionRecord), goal_id)
    misconceptions = _filter_goal(list_yaml_records(root, "misconceptions", MisconceptionRecord), goal_id)
    tests = _filter_goal(list_yaml_records(root, "tests", TestRecord), goal_id)
    references = _filter_goal(list_yaml_records(root, "references", ReferenceRecord), goal_id)

    open_loop_counts = {
        "unverified_claims": sum(1 for claim in claims if claim.status in {"unverified", "open_question"}),
        "weak_claims": sum(1 for claim in claims if claim.status in {"partially_correct", "misleading", "wrong"}),
        "trust_gaps": sum(1 for record in derivations if record.status != "trusted"),
        "confusions": sum(1 for record in distinctions if record.status in {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}),
        "misconceptions": sum(1 for record in misconceptions if record.status in {"active", "recurring"} or record.recurrence_count >= 2),
        "due_tests": sum(1 for record in tests if record.status in {"planned", "failed", "needs_retest"}),
        "due_reviews": len(due_review_items(root)),
    }
    top_open_loops = {
        "unverified_claims": [model_to_data(claim) for claim in claims if claim.status in {"unverified", "open_question"}][:3],
        "weak_claims": [model_to_data(claim) for claim in claims if claim.status in {"partially_correct", "misleading", "wrong"}][:3],
        "trust_gaps": [model_to_data(record) for record in derivations if record.status != "trusted"][:3],
        "confusions": [model_to_data(record) for record in distinctions if record.status in {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}][:3],
        "misconceptions": [model_to_data(record) for record in misconceptions if record.status in {"active", "recurring"} or record.recurrence_count >= 2][:3],
        "due_tests": [model_to_data(record) for record in tests if record.status in {"planned", "failed", "needs_retest"}][:3],
        "due_reviews": due_review_items(root)[:3],
    }

    ready_for_test = [
        *[_learning_item_view(record, "position") for record in positions if record.internalization_level in {"A0", "A1"}],
        *[_learning_item_view(record, "derivation") for record in derivations if record.record_intensity == "heavy" and record.status != "trusted"],
        *[_learning_item_view(record, "distinction") for record in distinctions if record.status in {"needs_test", "needs_retest", "partially_clear"}],
    ][:8]
    important_events = [
        event
        for event in sorted(load_events(root=root), key=lambda item: item.timestamp_utc, reverse=True)
        if event.event_type in IMPORTANT_ACTIVITY_TYPES
    ][:8]
    recent_references = sorted(references, key=lambda item: item.updated_at, reverse=True)[:6]
    next_actions = _dashboard_next_actions(root, claims, derivations, positions, distinctions, misconceptions, tests, references, goal)

    return {
        "active_goal": model_to_data(goal) if goal else None,
        "primary_next_action": next_actions[0] if next_actions else None,
        "secondary_next_actions": next_actions[1:4],
        "open_loop_counts": open_loop_counts,
        "top_open_loops": top_open_loops,
        "trust_gaps": top_open_loops["trust_gaps"],
        "ready_for_test": ready_for_test,
        "due_reviews": due_review_items(root)[:8],
        "recent_activity": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "summary": event.summary,
                "timestamp": event.timestamp_local.isoformat(),
            }
            for event in important_events
        ],
        "recent_references": [model_to_data(reference) for reference in recent_references],
    }


def _prompt(root: Path, prompt_type: str, payload: dict[str, Any]) -> ApiResponse:
    goal = None
    if prompt_type not in {"goal-intake", "weekly-review", "extract-references", "extract-positioning", "temporal-review"}:
        goal_id = payload.get("goal_id")
        goal = load_yaml_model(root / "data" / "goals" / f"{goal_id}.yaml", Goal) if goal_id else active_goal(root)
        if goal is None:
            return _error("No active goal found.", 404)

    if prompt_type == "goal-intake":
        return _ok({"prompt": goal_intake_prompt(payload.get("raw_goal"))})
    if prompt_type == "deep-research":
        return _ok({"prompt": deep_research_prompt(goal)})
    if prompt_type == "dynamic-positioning":
        policy = _load_resource(root, "policies", payload["policy_id"]) if payload.get("policy_id") else None
        return _ok({"prompt": dynamic_positioning_prompt(goal, payload.get("knowledge_point", ""), payload.get("current_context"), policy=policy)})
    if prompt_type == "refine-policy":
        return _ok({"prompt": refine_policy_prompt(goal)})
    if prompt_type == "classify-with-policy":
        policy = _load_resource(root, "policies", payload["policy_id"])
        return _ok(
            {
                "prompt": classify_with_policy_prompt(
                    goal,
                    payload.get("knowledge_point", ""),
                    policy,
                    current_user_state=payload.get("current_user_state"),
                    reference_hints=payload.get("reference_hints"),
                    deep_research_hints=payload.get("deep_research_hints"),
                )
            }
        )
    if prompt_type == "visual-suggest":
        return _ok({"prompt": visual_suggestion_prompt(goal, payload.get("topic", ""))})
    if prompt_type == "visual-explain":
        visual = _load_resource(root, "visuals", payload["visual_id"])
        visual_goal = load_yaml_model(root / "data" / "goals" / f"{visual.goal_id}.yaml", Goal)
        return _ok({"prompt": visual_explanation_prompt(visual_goal, visual)})
    if prompt_type == "claim-verification":
        claim = _load_resource(root, "claims", payload["claim_id"])
        claim_goal = load_yaml_model(root / "data" / "goals" / f"{claim.goal_id}.yaml", Goal)
        return _ok({"prompt": claim_verification_prompt(claim_goal, claim)})
    if prompt_type == "derivation-guidance":
        derivation = _load_resource(root, "derivations", payload["derivation_id"])
        derivation_goal = load_yaml_model(root / "data" / "goals" / f"{derivation.goal_id}.yaml", Goal)
        return _ok({"prompt": derivation_guidance_prompt(derivation_goal, derivation)})
    if prompt_type == "distinguish":
        distinction = _load_resource(root, "distinctions", payload["distinction_id"])
        distinction_goal = load_yaml_model(root / "data" / "goals" / f"{distinction.goal_id}.yaml", Goal)
        return _ok({"prompt": distinction_prompt(distinction_goal, distinction)})
    if prompt_type == "distinction-test":
        distinction = _load_resource(root, "distinctions", payload["distinction_id"])
        distinction_goal = load_yaml_model(root / "data" / "goals" / f"{distinction.goal_id}.yaml", Goal)
        return _ok({"prompt": distinction_test_prompt(distinction_goal, distinction)})
    if prompt_type == "misconception-correction":
        misconception = _load_resource(root, "misconceptions", payload["misconception_id"])
        misconception_goal = load_yaml_model(root / "data" / "goals" / f"{misconception.goal_id}.yaml", Goal)
        return _ok({"prompt": misconception_correction_prompt(misconception_goal, misconception)})
    if prompt_type == "temporal-review":
        lines = payload.get("timeline") or build_timeline(payload.get("target_id", ""), root=root)
        return _ok({"prompt": temporal_review_prompt(lines)})
    if prompt_type == "socratic":
        return _ok({"prompt": socratic_drill_prompt(goal, payload.get("topic", ""))})
    if prompt_type == "method-router":
        state = payload.get("state", "unknown_next_step")
        actions = recommend_methods(state).actions
        return _ok({"prompt": method_router_prompt(goal, state, payload.get("topic"), actions), "actions": actions})
    if prompt_type == "test-topic":
        return _ok({"prompt": test_topic_prompt(goal, payload.get("topic", ""))})
    if prompt_type == "test-record":
        test = _load_resource(root, "tests", payload["test_id"])
        test_goal = load_yaml_model(root / "data" / "goals" / f"{test.goal_id}.yaml", Goal)
        return _ok({"prompt": test_record_prompt(test_goal, test)})
    if prompt_type == "weekly-review":
        return _ok({"prompt": weekly_review_prompt()})
    if prompt_type == "extract-references":
        path = find_research_import(root, payload["import_id"])
        return _ok({"prompt": extract_references_prompt(path.stem, path.read_text(encoding="utf-8"))})
    if prompt_type == "extract-positioning":
        path = find_research_import(root, payload["import_id"])
        return _ok({"prompt": extract_positioning_from_research_prompt(path.stem, path.read_text(encoding="utf-8"))})
    return _error(f"Unknown prompt type: {prompt_type}", 404)


def _provider_settings(root: Path) -> ApiResponse:
    config = load_config(root)
    return _ok(public_config_summary(config))


def _provider_test(root: Path, provider_id: str) -> ApiResponse:
    config = load_config(root)
    provider = build_provider(config, provider_id)
    ok, message = provider.test_connection()
    return _ok({"ok": ok, "message": message}, 200 if ok else 422)


def _ai_run_text(root: Path, payload: dict[str, Any]) -> ApiResponse:
    if not payload.get("confirmed"):
        return _error("Connected-mode AI runs require explicit confirmation.", 400)
    prompt = str(payload.get("prompt") or "")
    if not prompt.strip():
        return _error("Prompt is required.", 400)
    provider_id = str(payload.get("provider_id") or "")
    config = load_config(root)
    provider = build_provider(config, provider_id)
    result = provider.run_chat(
        ChatRequest(
            system_prompt=(
                "You are assisting ai-learning-os. Treat selected records as learner state, not final truth. "
                "Do not invent facts absent from selected prompt/context."
            ),
            user_prompt=prompt,
            model=payload.get("model") or config.default_model,
        )
    )
    metadata_path = save_ai_run_artifact(
        root,
        result=result,
        prompt_text=prompt,
        prompt_type=str(payload.get("prompt_type") or "ui_prompt"),
        related_record_ids=[str(item) for item in payload.get("related_record_ids", [])],
    )
    metadata, response = load_ai_run(root, metadata_path.parent.name)
    return _ok({"item": metadata, "response": response, "preview": preview_as_dict(preview_payload(prompt))})


def handle_api_request(
    method: str,
    raw_path: str,
    payload: dict[str, Any] | None,
    root: Path | str = ".",
) -> ApiResponse:
    base = Path(root).resolve()
    parsed = urlparse(raw_path)
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    query = parse_qs(parsed.query)
    body = dict(payload or {})
    method = method.upper()

    try:
        if _is_new_api_route(parts):
            from .api.app import create_core_app
            from .db.database import Database

            database = Database(f"sqlite:///{base / 'data' / 'ai_learn_os.sqlite3'}")
            status, data = create_core_app(database=database).handle(method, parsed.path, body)
            return ApiResponse(status, data if isinstance(data, dict) else {"items": data})
        if parts == ["api", "dashboard"] and method == "GET":
            status = project_status(base)
            return _ok({"status": asdict(status), "next_actions": suggest_next_actions(base), "test_suggestions": suggest_tests(base)})
        if parts == ["api", "dashboard-view"] and method == "GET":
            return _ok(_dashboard_view(base))
        if parts == ["api", "learning-items"] and method == "GET":
            return _ok({"items": _learning_items(base)})
        if parts == ["api", "indexes", "refresh"] and method in {"POST", "GET"}:
            paths = refresh_indexes(base)
            return _ok({"message": "indexes refreshed", "directory": str(paths.directory), "summary": show_index(base)})
        if parts == ["api", "indexes"] and method == "GET":
            return _ok({"summary": show_index(base)})
        if parts == ["api", "indexes", "active-goal"] and method == "GET":
            paths = refresh_indexes(base)
            return _ok({"markdown": paths.active_goal_summary.read_text(encoding="utf-8")})
        if parts == ["api", "indexes", "open-loops"] and method == "GET":
            paths = refresh_indexes(base)
            return _ok({"markdown": paths.open_loops.read_text(encoding="utf-8")})
        if parts == ["api", "indexes", "recent"] and method == "GET":
            paths = refresh_indexes(base)
            return _ok({"markdown": paths.recent_activity.read_text(encoding="utf-8")})
        if parts[:3] == ["api", "indexes", "topic"] and len(parts) == 4 and method == "GET":
            return _ok({"markdown": topic_summary(base, parts[3])})
        if parts == ["api", "context", "policy"] and method == "GET":
            return _ok({"policy": context_policy_text()})
        if parts == ["api", "context", "build"] and method == "POST":
            pack = build_context_pack(
                base,
                task_type=body["task_type"],
                record_id=body.get("record_id"),
                topic=body.get("topic"),
                goal_id=body.get("goal_id"),
                budget=body.get("budget", "medium"),
            )
            return _ok({"path": str(pack.path), "size_bytes": pack.size_bytes, "markdown": pack.path.read_text(encoding="utf-8")})
        if parts == ["api", "settings", "providers"] and method == "GET":
            return _provider_settings(base)
        if parts[:4] == ["api", "settings", "providers", "test"] and len(parts) == 5 and method == "POST":
            return _provider_test(base, parts[4])
        if parts == ["api", "ai", "runs"] and method == "GET":
            return _ok({"items": list_ai_runs(base)})
        if parts[:3] == ["api", "ai", "runs"] and len(parts) == 4 and method == "GET":
            metadata, response = load_ai_run(base, parts[3])
            return _ok({"item": metadata, "response": response})
        if parts == ["api", "ai", "run-text"] and method == "POST":
            return _ai_run_text(base, body)
        if parts == ["api", "validate"] and method == "GET":
            report = validate_project(base)
            return _ok({"ok": report.ok, "errors": report.errors, "warnings": report.warnings}, 200 if report.ok else 422)
        if parts == ["api", "method", "suggest"] and method == "POST":
            recommendation = recommend_methods(body.get("state", "unknown_next_step"))
            return _ok({"state": str(recommendation.state), "actions": recommendation.actions, "rationale": recommendation.rationale})
        if parts == ["api", "tests", "suggest"] and method == "GET":
            return _ok({"items": suggest_tests(base)})
        if parts == ["api", "events"] and method == "GET":
            return _ok({"items": load_events(query.get("month", [None])[0], root=base)})
        if parts[:3] == ["api", "events", "timeline"] and len(parts) == 4 and method == "GET":
            return _ok({"target_id": parts[3], "timeline": build_timeline(parts[3], root=base), "summary": summarize_events_for_record(parts[3], root=base)})
        if parts == ["api", "research-imports"] and method == "GET":
            return _list_research_imports(base)
        if parts[:2] == ["api", "prompts"] and len(parts) == 3 and method == "POST":
            return _prompt(base, parts[2], body)
        if parts == ["api", "reviews"] and method == "GET":
            return _list_reviews(base)
        if parts == ["api", "reviews", "weekly"] and method == "POST":
            path = generate_weekly_review(base)
            return _ok({"path": str(path), "markdown": Path(path).read_text(encoding="utf-8")})
        if parts == ["api", "reviews", "due"] and method == "GET":
            return _ok({"items": due_review_items(base)})
        if parts[:2] == ["api", "reviews"] and len(parts) == 3 and method == "GET":
            return _show_review(base, parts[2])

        if parts == ["api", "goals", "active"] and method == "GET":
            goal = active_goal(base)
            return _ok({"item": goal}) if goal else _error("No active goal found.", 404)
        if parts == ["api", "goals", "active"] and method == "POST":
            return _set_active_goal(base, body["goal_id"])

        if parts == ["api", "sessions"] and method == "GET":
            return _list_sessions(base)
        if parts == ["api", "sessions"] and method == "POST":
            return _save_session_resource(base, body)
        if parts[:2] == ["api", "sessions"] and len(parts) == 3:
            if method == "GET":
                return _show_session(base, parts[2])
            if method in {"PUT", "PATCH"}:
                return _save_session_resource(base, body, parts[2])

        if len(parts) >= 2 and parts[0] == "api" and parts[1] in RESOURCES:
            resource = parts[1]
            if len(parts) == 2 and method == "GET":
                return _list_resource(base, resource, query)
            if len(parts) == 2 and method == "POST":
                return _ok({"item": _save_resource(base, resource, body)}, 201)
            if len(parts) == 3 and method == "GET":
                return _ok({"item": _load_resource(base, resource, parts[2])})
            if len(parts) == 3 and method in {"PUT", "PATCH"}:
                return _ok({"item": _save_resource(base, resource, body, parts[2])})

        return _error(f"Not found: {raw_path}", 404)
    except FileNotFoundError as exc:
        return _error(str(exc), 404)
    except Exception as exc:
        return _error(str(exc), 400)


def _is_new_api_route(parts: list[str]) -> bool:
    if tuple(parts[:2]) in {
        ("api", "chat"),
        ("api", "run-next"),
        ("api", "projects"),
        ("api", "system-settings"),
        ("api", "references"),
        ("api", "state-updates"),
    }:
        return True
    return False

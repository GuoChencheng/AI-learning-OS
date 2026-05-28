from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from .events import load_events
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
from .review import due_review_items
from .storage import active_goal, list_sessions, list_yaml_records


@dataclass(frozen=True)
class IndexPaths:
    directory: Path
    active_goal_summary: Path
    open_loops: Path
    recent_activity: Path
    reference_index: Path
    manifest: Path
    topic_index: Path


RECORD_MODELS: dict[str, type[BaseModel]] = {
    "goals": Goal,
    "positioning": PositionDecision,
    "claims": ClaimRecord,
    "derivations": DerivationRecord,
    "references": ReferenceRecord,
    "tests": TestRecord,
    "distinctions": DistinctionRecord,
    "misconceptions": MisconceptionRecord,
    "clusters": ConceptClusterRecord,
    "policies": ClassificationPolicy,
    "visuals": VisualResourceRecord,
}

TOPIC_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def _text_topics(text: str) -> list[str]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    topics = [word for word in words if len(word) > 2]
    topics.extend(f"{left}_{right}" for left, right in zip(words, words[1:]) if len(left) > 2 and len(right) > 2)
    topics.extend(TOPIC_TOKEN_RE.findall(text))
    return topics


def _topic_variants(topic: str) -> list[str]:
    normalized = topic.strip()
    if not normalized:
        return []
    variants = [normalized]
    lower = normalized.lower()
    if lower != normalized:
        variants.append(lower)
    parts = [part for part in lower.split("_") if part]
    if len(parts) >= 2:
        variants.extend("_".join(parts[index : index + 2]) for index in range(len(parts) - 1))
    return variants


def index_paths(root: Path | str = ".") -> IndexPaths:
    directory = Path(root) / "data" / "indexes"
    return IndexPaths(
        directory=directory,
        active_goal_summary=directory / "active_goal_summary.md",
        open_loops=directory / "open_loops.md",
        recent_activity=directory / "recent_activity.md",
        reference_index=directory / "reference_index.yaml",
        manifest=directory / "record_manifest.jsonl",
        topic_index=directory / "topic_index.yaml",
    )


def _safe_attr(record: object, name: str) -> Any:
    return getattr(record, name, None)


def _record_label(record: object) -> str:
    return str(
        _safe_attr(record, "topic")
        or _safe_attr(record, "title")
        or _safe_attr(record, "knowledge_point")
        or _safe_attr(record, "text")
        or _safe_attr(record, "statement")
        or _safe_attr(record, "id")
    )


def _record_topics(record: object) -> list[str]:
    direct: list[str] = []
    if isinstance(record, Goal):
        direct.extend(record.priority_topics)
        direct.extend(TOPIC_TOKEN_RE.findall(record.title))
    elif isinstance(record, PositionDecision):
        direct.append(record.knowledge_point)
    elif isinstance(record, DerivationRecord):
        direct.append(record.topic)
    elif isinstance(record, ReferenceRecord):
        direct.extend(record.topics)
    elif isinstance(record, TestRecord):
        direct.append(record.topic)
    elif isinstance(record, DistinctionRecord):
        direct.extend(record.concepts)
        direct.extend(_text_topics(record.title.replace(" vs ", " ")))
    elif isinstance(record, MisconceptionRecord):
        direct.extend(record.related_topics)
        direct.extend(_text_topics(record.statement))
    elif isinstance(record, ConceptClusterRecord):
        direct.extend(record.concepts)
        direct.extend(_text_topics(record.title))
    elif isinstance(record, ClassificationPolicy):
        direct.extend(_text_topics(record.title))
    elif isinstance(record, VisualResourceRecord):
        direct.append(record.topic)
    elif isinstance(record, ClaimRecord):
        direct.extend(_text_topics(" ".join([record.text, record.context, record.next_action])))
    elif isinstance(record, SessionFootprint):
        direct.append(record.topic)

    seen: set[str] = set()
    topics: list[str] = []
    for topic in direct:
        for normalized in _topic_variants(str(topic)):
            if normalized and normalized not in seen:
                seen.add(normalized)
                topics.append(normalized)
    return topics


def _manifest_line(root: Path, directory: str, path: Path, record: object) -> dict[str, Any]:
    return {
        "id": _safe_attr(record, "id"),
        "type": directory,
        "goal_id": _safe_attr(record, "goal_id"),
        "topic": _safe_attr(record, "topic") or _safe_attr(record, "knowledge_point"),
        "title": _safe_attr(record, "title") or _record_label(record),
        "status": _safe_attr(record, "status") or _safe_attr(record, "current_status") or _safe_attr(record, "reading_status"),
        "epistemic_status": _safe_attr(record, "epistemic_status"),
        "position": _safe_attr(record, "position"),
        "internalization_level": _safe_attr(record, "internalization_level"),
        "record_intensity": _safe_attr(record, "record_intensity"),
        "updated_at": str(_safe_attr(record, "updated_at") or _safe_attr(record, "created_at") or ""),
        "path": str(path.relative_to(root)),
    }


def _all_record_lines(root: Path) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for directory, model_cls in RECORD_MODELS.items():
        for record in list_yaml_records(root, directory, model_cls):
            path = root / "data" / directory / f"{getattr(record, 'id')}.yaml"
            lines.append(_manifest_line(root, directory, path, record))

    for path, session, _ in list_sessions(root):
        lines.append(_manifest_line(root, "sessions", path, session))

    def sort_key(line: dict[str, Any]) -> tuple[str, str]:
        return (str(line.get("updated_at") or ""), str(line.get("id") or ""))

    return sorted(lines, key=sort_key, reverse=True)


def _active_goal_markdown(root: Path) -> str:
    goal = active_goal(root)
    if goal is None:
        return "# Active Goal Summary\n\nNo active goal recorded.\n"
    topics = ", ".join(goal.priority_topics) if goal.priority_topics else "None recorded"
    return f"""# Active Goal Summary

- id: {goal.id}
- title: {goal.title}
- main_goal: {goal.main_goal}
- stage_goal: {goal.stage_goal}
- transfer_goal: {goal.transfer_goal}
- external_goal: {goal.external_goal}
- priority_topics: {topics}
- updated_at: {goal.updated_at.isoformat()}

This summary is derived from the goal record. It is not a source of truth.
"""


def _reference_index(root: Path) -> list[dict[str, Any]]:
    references = list_yaml_records(root, "references", ReferenceRecord)
    return [
        {
            "id": reference.id,
            "title": reference.title,
            "reference_type": str(reference.reference_type),
            "topics": reference.topics,
            "path_or_url": reference.path_or_url,
            "reading_status": str(reference.reading_status),
            "relevance_to_goal": reference.relevance_to_goal,
            "usage_stage": str(reference.usage_stage),
        }
        for reference in references
    ]


def _topic_index(root: Path) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = {}

    def add(topic: str, directory: str, record_id: str) -> None:
        bucket = index.setdefault(topic, {})
        items = bucket.setdefault(directory, [])
        if record_id not in items:
            items.append(record_id)

    for directory, model_cls in RECORD_MODELS.items():
        for record in list_yaml_records(root, directory, model_cls):
            for topic in _record_topics(record):
                add(topic, directory, getattr(record, "id"))

    for _, session, _ in list_sessions(root):
        for topic in _record_topics(session):
            add(topic, "sessions", session.id)

    return {topic: {key: sorted(values) for key, values in sorted(groups.items())} for topic, groups in sorted(index.items())}


def _open_loops_markdown(root: Path) -> str:
    claims = list_yaml_records(root, "claims", ClaimRecord)
    derivations = list_yaml_records(root, "derivations", DerivationRecord)
    positions = list_yaml_records(root, "positioning", PositionDecision)
    references = list_yaml_records(root, "references", ReferenceRecord)
    tests = list_yaml_records(root, "tests", TestRecord)
    distinctions = list_yaml_records(root, "distinctions", DistinctionRecord)
    misconceptions = list_yaml_records(root, "misconceptions", MisconceptionRecord)

    sections: list[tuple[str, list[str]]] = [
        (
            "Unverified Claims",
            [f"- {claim.id}: {claim.text} [{claim.status}, {claim.record_intensity}]" for claim in claims if claim.status in {"unverified", "open_question"}],
        ),
        (
            "Partially Correct Or Misleading Claims",
            [f"- {claim.id}: {claim.text} [{claim.status}]" for claim in claims if claim.status in {"partially_correct", "misleading", "wrong"}],
        ),
        (
            "Derivations Not Trusted",
            [f"- {record.id}: {record.topic} [{record.status}, {record.record_intensity}]" for record in derivations if record.status != "trusted"],
        ),
        (
            "Distinctions Needing Tests",
            [f"- {record.id}: {record.title} [{record.status}, confusions={record.confusion_count}]" for record in distinctions if record.status in {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}],
        ),
        (
            "Misconceptions Recurring",
            [f"- {record.id}: {record.statement} [{record.status}, recurrences={record.recurrence_count}]" for record in misconceptions if record.status == "recurring" or record.recurrence_count >= 2],
        ),
        (
            "Tests Due Or Failed",
            [f"- {record.id}: {record.topic} [{record.status}]" for record in tests if record.status in {"failed", "needs_retest"} or record.next_retest_at],
        ),
        (
            "Positioning Revisit Triggers",
            [f"- {record.id}: {record.knowledge_point} -> {', '.join(record.revisit_when)}" for record in positions if record.revisit_when],
        ),
        (
            "Core References Unread",
            [f"- {record.id}: {record.title}" for record in references if record.usage_stage == "core_learning" and record.reading_status == "unread"],
        ),
        ("Review Due Or Overdue", [f"- {item}" for item in due_review_items(root)]),
    ]

    lines = ["# Open Loops", "", "Derived summary. Use source records for edits.", ""]
    for title, items in sections:
        lines.extend([f"## {title}", ""])
        lines.extend(items or ["- None recorded."])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _recent_activity_markdown(root: Path, manifest_lines: list[dict[str, Any]]) -> str:
    events = sorted(load_events(root=root), key=lambda event: event.timestamp_utc, reverse=True)[:20]
    sessions = sorted(list_sessions(root), key=lambda item: item[1].created_at, reverse=True)[:10]
    recent_records = manifest_lines[:10]

    lines = ["# Recent Activity", "", "Compact activity index. Session bodies and reference contents are intentionally omitted.", ""]
    lines.extend(["## Last Events", ""])
    lines.extend([f"- {event.timestamp_local.isoformat()} {event.event_type}: {event.summary}" for event in events] or ["- None recorded."])
    lines.extend(["", "## Recent Sessions", ""])
    lines.extend([f"- {session.created_at.isoformat()} {session.id}: {session.topic} ({session.mode})" for _, session, _ in sessions] or ["- None recorded."])
    lines.extend(["", "## Recently Updated Records", ""])
    lines.extend([f"- {line['id']} [{line['type']}] {line.get('title') or line.get('topic')}" for line in recent_records] or ["- None recorded."])
    return "\n".join(lines).rstrip() + "\n"


def refresh_indexes(root: Path | str = ".") -> IndexPaths:
    base = Path(root)
    paths = index_paths(base)
    paths.directory.mkdir(parents=True, exist_ok=True)

    manifest_lines = _all_record_lines(base)
    paths.active_goal_summary.write_text(_active_goal_markdown(base), encoding="utf-8")
    paths.open_loops.write_text(_open_loops_markdown(base), encoding="utf-8")
    paths.recent_activity.write_text(_recent_activity_markdown(base, manifest_lines), encoding="utf-8")
    paths.reference_index.write_text(yaml.safe_dump(_reference_index(base), sort_keys=False, allow_unicode=True), encoding="utf-8")
    paths.topic_index.write_text(yaml.safe_dump(_topic_index(base), sort_keys=True, allow_unicode=True), encoding="utf-8")
    with paths.manifest.open("w", encoding="utf-8") as handle:
        for line in manifest_lines:
            handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
    return paths


def load_manifest(root: Path | str = ".") -> list[dict[str, Any]]:
    path = index_paths(root).manifest
    if not path.exists():
        refresh_indexes(root)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_topic_index(root: Path | str = ".") -> dict[str, dict[str, list[str]]]:
    path = index_paths(root).topic_index
    if not path.exists():
        refresh_indexes(root)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def show_index(root: Path | str = ".") -> str:
    paths = refresh_indexes(root)
    manifest_count = len(load_manifest(root))
    topics = load_topic_index(root)
    return "\n".join(
        [
            f"Index directory: {paths.directory}",
            f"Manifest records: {manifest_count}",
            f"Indexed topics: {len(topics)}",
            f"Active goal summary: {paths.active_goal_summary}",
            f"Open loops: {paths.open_loops}",
            f"Recent activity: {paths.recent_activity}",
            f"Reference index: {paths.reference_index}",
            f"Topic index: {paths.topic_index}",
        ]
    )


def topic_summary(root: Path | str, topic: str) -> str:
    refresh_indexes(root)
    topic_index = load_topic_index(root)
    bucket = topic_index.get(topic)
    if not bucket:
        return f"No indexed records for topic: {topic}"
    lines = [f"# Topic Index: {topic}", ""]
    for directory, ids in sorted(bucket.items()):
        lines.append(f"## {directory}")
        lines.extend(f"- {record_id}" for record_id in ids)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

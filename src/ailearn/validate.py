from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from .events import EVENT_TYPES, LearningEvent
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
from .storage import load_session, load_yaml_model


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


YAML_RECORDS = {
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


def _format_validation_error(path: Path, error: Exception) -> str:
    if isinstance(error, ValidationError):
        return f"{path}: {error}"
    return f"{path}: {type(error).__name__}: {error}"


def validate_project(root: Path | str = ".") -> ValidationReport:
    base = Path(root)
    report = ValidationReport()
    goal_ids: set[str] = set()
    referenced: list[tuple[Path, str]] = []
    record_ids: dict[str, set[str]] = {directory: set() for directory in YAML_RECORDS}
    related_references: list[tuple[Path, str, str, str]] = []
    policy_references: list[tuple[Path, str]] = []
    generic_related_references: list[tuple[Path, str, str]] = []

    for directory, model_cls in YAML_RECORDS.items():
        data_dir = base / "data" / directory
        if not data_dir.exists():
            report.errors.append(f"{data_dir}: missing directory")
            continue
        for path in sorted(data_dir.glob("*.yaml")):
            try:
                record = load_yaml_model(path, model_cls)
            except Exception as exc:
                report.errors.append(_format_validation_error(path, exc))
                continue
            if isinstance(record, Goal):
                record_ids[directory].add(record.id)
                goal_ids.add(record.id)
            elif isinstance(record, PositionDecision):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
                if record.policy_id:
                    policy_references.append((path, record.policy_id))
                if record.position != "A_no_ai_internalization" and record.internalization_level != "none":
                    report.warnings.append(
                        f"{path}: internalization_level {record.internalization_level} is usually meaningful only for A_no_ai_internalization"
                    )
            elif isinstance(record, ClassificationPolicy):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
            elif isinstance(record, VisualResourceRecord):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
                generic_related_references.extend((path, related_id, "related_record_ids") for related_id in record.related_record_ids)
            elif isinstance(record, DistinctionRecord):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
                if len(record.concepts) < 2:
                    report.warnings.append(f"{path}: DistinctionRecord usually needs at least two concepts")
                related_references.extend((path, "claims", claim_id, "related_claim_ids") for claim_id in record.related_claim_ids)
                related_references.extend((path, "tests", test_id, "related_test_ids") for test_id in record.related_test_ids)
                related_references.extend((path, "sessions", session_id, "related_session_ids") for session_id in record.related_session_ids)
            elif isinstance(record, MisconceptionRecord):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
                related_references.extend((path, "claims", claim_id, "related_claim_ids") for claim_id in record.related_claim_ids)
                related_references.extend((path, "distinctions", distinction_id, "related_distinction_ids") for distinction_id in record.related_distinction_ids)
                related_references.extend((path, "sessions", session_id, "related_session_ids") for session_id in record.related_session_ids)
            elif isinstance(record, ConceptClusterRecord):
                record_ids[directory].add(record.id)
                referenced.append((path, record.goal_id))
                related_references.extend((path, "distinctions", distinction_id, "related_distinction_ids") for distinction_id in record.related_distinction_ids)
                related_references.extend((path, "positioning", position_id, "related_position_ids") for position_id in record.related_position_ids)
                related_references.extend((path, "sessions", session_id, "related_session_ids") for session_id in record.related_session_ids)
            elif hasattr(record, "goal_id"):
                record_ids[directory].add(getattr(record, "id"))
                referenced.append((path, getattr(record, "goal_id")))

    sessions_dir = base / "data" / "sessions"
    if not sessions_dir.exists():
        report.errors.append(f"{sessions_dir}: missing directory")
    else:
        for path in sorted(sessions_dir.glob("*.md")):
            try:
                session, _ = load_session(path)
            except Exception as exc:
                report.errors.append(_format_validation_error(path, exc))
                continue
            if not isinstance(session, SessionFootprint):
                report.errors.append(f"{path}: invalid session metadata")
                continue
            record_ids.setdefault("sessions", set()).add(session.id)
            referenced.append((path, session.goal_id))

    for path, goal_id in referenced:
        if goal_id not in goal_ids:
            report.errors.append(f"{path}: broken goal_id reference: {goal_id}")

    for path, directory, record_id, field_name in related_references:
        if record_id not in record_ids.get(directory, set()):
            report.errors.append(f"{path}: broken {field_name} reference to {directory}: {record_id}")

    for path, policy_id in policy_references:
        if policy_id not in record_ids.get("policies", set()):
            report.errors.append(f"{path}: broken policy_id reference: {policy_id}")

    all_record_ids = set().union(*record_ids.values()) if record_ids else set()
    for path, record_id, field_name in generic_related_references:
        if record_id not in all_record_ids:
            report.errors.append(f"{path}: broken {field_name} reference: {record_id}")

    events_dir = base / "data" / "events"
    if not events_dir.exists():
        report.errors.append(f"{events_dir}: missing directory")
    else:
        for path in sorted(events_dir.glob("*.jsonl")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    event = LearningEvent.model_validate(json.loads(line))
                except Exception as exc:
                    report.errors.append(f"{path}:{line_number}: malformed event JSONL: {exc}")
                    continue
                if event.event_type not in EVENT_TYPES:
                    report.errors.append(f"{path}:{line_number}: invalid event_type: {event.event_type}")
                if event.goal_id and event.goal_id not in goal_ids:
                    report.errors.append(f"{path}:{line_number}: broken event goal_id reference: {event.goal_id}")

    indexes_dir = base / "data" / "indexes"
    if not indexes_dir.exists():
        report.errors.append(f"{indexes_dir}: missing directory")
    else:
        manifest_path = indexes_dir / "record_manifest.jsonl"
        if manifest_path.exists():
            for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except Exception as exc:
                    report.errors.append(f"{manifest_path}:{line_number}: malformed manifest JSONL: {exc}")
                    continue
                for key in ["id", "type", "path"]:
                    if key not in entry:
                        report.errors.append(f"{manifest_path}:{line_number}: missing manifest field: {key}")
                record_path = base / str(entry.get("path", ""))
                if entry.get("path") and not record_path.exists():
                    report.errors.append(f"{manifest_path}:{line_number}: manifest path does not exist: {entry.get('path')}")
        topic_index_path = indexes_dir / "topic_index.yaml"
        if topic_index_path.exists():
            try:
                topic_index = yaml.safe_load(topic_index_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                report.errors.append(f"{topic_index_path}: malformed topic_index YAML: {exc}")
                topic_index = {}
            valid_ids = all_record_ids | record_ids.get("sessions", set())
            for topic, groups in topic_index.items():
                if not isinstance(groups, dict):
                    report.errors.append(f"{topic_index_path}: topic {topic} must map to record groups")
                    continue
                for group, ids in groups.items():
                    if not isinstance(ids, list):
                        report.errors.append(f"{topic_index_path}: topic {topic}/{group} must be a list")
                        continue
                    for record_id in ids:
                        if record_id not in valid_ids:
                            report.errors.append(f"{topic_index_path}: topic {topic} references missing record id: {record_id}")
        reference_index_path = indexes_dir / "reference_index.yaml"
        if reference_index_path.exists():
            try:
                yaml.safe_load(reference_index_path.read_text(encoding="utf-8")) or []
            except Exception as exc:
                report.errors.append(f"{reference_index_path}: malformed reference_index YAML: {exc}")

    context_dir = base / "data" / "context_packs"
    if not context_dir.exists():
        report.errors.append(f"{context_dir}: missing directory")
    else:
        for path in sorted(context_dir.glob("*.md")):
            size = path.stat().st_size
            if size > 100_000:
                report.errors.append(f"{path}: context pack exceeds default validation size limit: {size} bytes")

    ai_runs_dir = base / "data" / "ai_runs"
    if not ai_runs_dir.exists():
        report.errors.append(f"{ai_runs_dir}: missing directory")
    else:
        for path in sorted(ai_runs_dir.glob("*/metadata.yaml")):
            try:
                metadata = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                report.errors.append(f"{path}: malformed AI run metadata YAML: {exc}")
                continue
            for key in ["id", "provider", "model", "prompt_type", "created_at", "response_path", "user_review_status"]:
                if key not in metadata:
                    report.errors.append(f"{path}: missing AI run metadata field: {key}")
            if metadata.get("user_review_status") not in {"unreviewed", "accepted", "partially_accepted", "rejected", "archived"}:
                report.errors.append(f"{path}: invalid user_review_status: {metadata.get('user_review_status')}")
            response_path = Path(str(metadata.get("response_path", "")))
            if response_path and not response_path.is_absolute():
                response_path = base / response_path
            if metadata.get("response_path") and not response_path.exists():
                report.errors.append(f"{path}: missing AI run response file: {metadata.get('response_path')}")

    return report

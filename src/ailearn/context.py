from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .events import build_timeline
from .ids import now_utc
from .indexes import index_paths, load_manifest, load_topic_index, refresh_indexes


@dataclass(frozen=True)
class ContextPack:
    path: Path
    task_type: str
    budget: str
    record_count: int
    size_bytes: int


BUDGET_CAPS = {
    "small": {"related": 5, "timeline": 0, "references": 0, "session_excerpt": 0},
    "medium": {"related": 10, "timeline": 12, "references": 8, "session_excerpt": 0},
    "large": {"related": 20, "timeline": 25, "references": 12, "session_excerpt": 1200},
}

TASK_PRIORITIES: dict[str, list[str]] = {
    "verify_claim": ["claims", "distinctions", "misconceptions", "positioning", "sessions", "references"],
    "derivation_guidance": ["derivations", "claims", "tests", "positioning", "sessions", "references"],
    "positioning": ["positioning", "policies", "claims", "derivations", "sessions", "references"],
    "distinction": ["distinctions", "misconceptions", "claims", "tests", "sessions"],
    "misconception": ["misconceptions", "claims", "distinctions", "sessions", "tests"],
    "test_topic": ["claims", "derivations", "positioning", "distinctions", "misconceptions", "tests", "sessions", "references"],
    "weekly_review": ["claims", "derivations", "distinctions", "misconceptions", "tests", "positioning", "references"],
    "temporal_review": ["events", "claims", "derivations", "distinctions", "misconceptions", "tests"],
    "method_routing": ["sessions", "claims", "derivations", "positioning", "tests"],
    "reference_review": ["references", "claims", "positioning", "sessions"],
    "goal_intake": ["goals", "policies"],
    "deep_research": ["goals", "policies", "references"],
    "extract_references": ["references", "goals"],
}


def context_policy_text() -> str:
    return """AI Context Loading Policy

1. Read AGENTS.md, docs/core_methodology.md, and docs/ai_context_protocol.md first.
2. Identify task type before reading learner data.
3. Build or inspect a task-specific context pack.
4. Load the primary record and only selected related records.
5. Do not read all local files, all sessions, all references, or all Deep Research imports by default.
6. References are durable source metadata, not a knowledge database.
7. Deep Research is external guidance, not final truth.
8. AI may assist strategy, verification, and prompt generation, but must not replace no-AI internalization.
"""


def _read_optional(path: Path, fallback: str) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else fallback


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return text[:80] or "context"


def _manifest_by_id(manifest: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(line.get("id")): line for line in manifest if line.get("id")}


def _topics_for_record(record_id: str, topic_index: dict[str, dict[str, list[str]]]) -> list[str]:
    topics: list[str] = []
    for topic, groups in topic_index.items():
        if any(record_id in ids for ids in groups.values()):
            topics.append(topic)
    return topics


def _record_ids_for_topic(topic: str, topic_index: dict[str, dict[str, list[str]]]) -> list[str]:
    ids: list[str] = []
    for values in topic_index.get(topic, {}).values():
        for record_id in values:
            if record_id not in ids:
                ids.append(record_id)
    return ids


def _priority_key(task_type: str, line: dict[str, Any]) -> tuple[int, str]:
    priorities = TASK_PRIORITIES.get(task_type, [])
    record_type = str(line.get("type") or "")
    try:
        priority = priorities.index(record_type)
    except ValueError:
        priority = len(priorities) + 1
    return (priority, str(line.get("updated_at") or ""))


def _select_related(
    task_type: str,
    manifest: list[dict[str, Any]],
    topic_index: dict[str, dict[str, list[str]]],
    *,
    record_id: str | None,
    topic: str | None,
    goal_id: str | None,
    budget: str,
) -> list[dict[str, Any]]:
    by_id = _manifest_by_id(manifest)
    candidate_ids: list[str] = []
    topics = [topic] if topic else []
    if record_id:
        topics.extend(_topics_for_record(record_id, topic_index))
    for item in topics:
        if item:
            candidate_ids.extend(_record_ids_for_topic(item, topic_index))

    if task_type == "weekly_review":
        candidate_ids.extend(str(line.get("id")) for line in manifest)

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        if not candidate_id or candidate_id == record_id or candidate_id in seen:
            continue
        line = by_id.get(candidate_id)
        if line is None:
            continue
        if goal_id and line.get("goal_id") not in {goal_id, None, ""}:
            continue
        seen.add(candidate_id)
        candidates.append(line)

    caps = BUDGET_CAPS[budget]
    return sorted(candidates, key=lambda line: _priority_key(task_type, line))[: caps["related"]]


def _primary_record_section(root: Path, manifest: list[dict[str, Any]], record_id: str | None) -> tuple[str, dict[str, Any] | None]:
    if not record_id:
        return "No primary record id supplied.", None
    line = _manifest_by_id(manifest).get(record_id)
    if line is None:
        return f"Primary record not found in manifest: {record_id}", None
    path = root / str(line["path"])
    if not path.exists():
        return f"Primary record path missing: {path}", line
    raw = path.read_text(encoding="utf-8")
    return f"Path: {line['path']}\n\n```yaml\n{raw.strip()}\n```", line


def _related_section(related: list[dict[str, Any]]) -> str:
    if not related:
        return "- None selected."
    lines = []
    for item in related:
        lines.append(
            "- "
            + f"{item.get('id')} [{item.get('type')}] "
            + f"title={item.get('title') or item.get('topic')} "
            + f"status={item.get('status') or 'n/a'} "
            + f"position={item.get('position') or 'n/a'} "
            + f"intensity={item.get('record_intensity') or 'n/a'} "
            + f"path={item.get('path')}"
        )
    return "\n".join(lines)


def _reference_metadata(root: Path, related: list[dict[str, Any]], topic: str | None, limit: int) -> str:
    if limit <= 0:
        return "Reference metadata omitted for small budget."
    path = index_paths(root).reference_index
    if not path.exists():
        refresh_indexes(root)
    references = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    related_ids = {str(item.get("id")) for item in related if item.get("type") == "references"}
    selected = []
    for reference in references:
        topics = reference.get("topics") or []
        if reference.get("id") in related_ids or (topic and topic in topics):
            selected.append(reference)
    if not selected:
        return "- None selected."
    return "\n".join(
        f"- {ref['id']}: {ref['title']} [{ref['reference_type']}, {ref['usage_stage']}, {ref['reading_status']}] {ref['path_or_url']}"
        for ref in selected[:limit]
    )


def _session_excerpts(root: Path, topic: str | None, limit_chars: int) -> str:
    if limit_chars <= 0:
        return ""
    sessions_dir = root / "data" / "sessions"
    if not sessions_dir.exists():
        return "- None selected."
    lines: list[str] = []
    for path in sorted(sessions_dir.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8")
        if topic and topic not in text:
            continue
        excerpt = text[:limit_chars].strip()
        lines.append(f"### {path.name}\n\n```markdown\n{excerpt}\n```")
        if len(lines) >= 3:
            break
    return "\n\n".join(lines) if lines else "- None selected."


def build_context_pack(
    root: Path | str = ".",
    *,
    task_type: str,
    record_id: str | None = None,
    topic: str | None = None,
    goal_id: str | None = None,
    output: Path | str | None = None,
    budget: str = "medium",
) -> ContextPack:
    if budget not in BUDGET_CAPS:
        raise ValueError(f"Unknown context budget: {budget}")
    base = Path(root)
    refresh_indexes(base)
    manifest = load_manifest(base)
    topic_index = load_topic_index(base)
    caps = BUDGET_CAPS[budget]

    primary, primary_line = _primary_record_section(base, manifest, record_id)
    resolved_topic = topic or (primary_line or {}).get("topic") or (primary_line or {}).get("title")
    resolved_goal_id = goal_id or (primary_line or {}).get("goal_id")
    related = _select_related(
        task_type,
        manifest,
        topic_index,
        record_id=record_id,
        topic=str(resolved_topic) if resolved_topic else None,
        goal_id=str(resolved_goal_id) if resolved_goal_id else None,
        budget=budget,
    )

    core_methodology = _read_optional(
        base / "docs" / "core_methodology.md",
        "Core methodology doc missing. Use project identity: local learning state, not world knowledge.",
    )
    active_summary = _read_optional(index_paths(base).active_goal_summary, "No active goal summary generated.")
    open_loops = _read_optional(index_paths(base).open_loops, "No open loops generated.") if task_type == "weekly_review" else ""
    recent = _read_optional(index_paths(base).recent_activity, "No recent activity generated.") if task_type in {"weekly_review", "method_routing"} else ""

    timeline_lines = build_timeline(record_id, root=base)[: caps["timeline"]] if record_id and caps["timeline"] else []
    timeline = "\n".join(f"- {line}" for line in timeline_lines) if timeline_lines else "- Omitted or no timeline events selected."
    reference_metadata = _reference_metadata(base, related, str(resolved_topic) if resolved_topic else None, caps["references"])
    session_excerpts = _session_excerpts(base, str(resolved_topic) if resolved_topic else None, caps["session_excerpt"])

    content = f"""# AI Context Pack

- Task type: {task_type}
- Budget: {budget}
- Primary id: {record_id or 'none'}
- Topic: {resolved_topic or 'none'}
- Goal id: {resolved_goal_id or goal_id or 'active/default'}

## Loading Instruction

Do not read all files unless necessary. Do not read all local files, all sessions, all references, or all Deep Research imports by default. Use this compact pack first, then request or inspect additional raw files only when the task clearly needs them.

## Base Methodology Summary

{core_methodology.strip()[:3000]}

## Active Goal Summary

{active_summary.strip()}

## Task Statement

Use the local learning-state records below for `{task_type}`. Keep deterministic local evidence separate from AI interpretation. Do not treat references or Deep Research guidance as final truth.

## Primary Record

{primary}

## Related Records Selected From Manifest

{_related_section(related)}

## Compact Event Timeline

{timeline}

## Reference Metadata

{reference_metadata}
"""
    if open_loops:
        content += f"\n## Open Loops Index\n\n{open_loops.strip()}\n"
    if recent:
        content += f"\n## Recent Activity Index\n\n{recent.strip()}\n"
    if budget == "large":
        content += f"\n## Selected Session Excerpts\n\n{session_excerpts}\n"

    output_path = Path(output) if output else base / "data" / "context_packs" / f"{_slug(task_type)}-{_slug(record_id or topic or 'general')}-{budget}-{now_utc().strftime('%Y%m%d%H%M%S%f')}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return ContextPack(
        path=output_path,
        task_type=task_type,
        budget=budget,
        record_count=1 + len(related),
        size_bytes=output_path.stat().st_size,
    )


def show_context_pack(**kwargs: Any) -> str:
    pack = build_context_pack(**kwargs)
    return pack.path.read_text(encoding="utf-8")

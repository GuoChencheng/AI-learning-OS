from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

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

ModelT = TypeVar("ModelT", bound=BaseModel)

DATA_DIRS = [
    "goals",
    "positioning",
    "claims",
    "derivations",
    "sessions",
    "reviews",
    "research_imports",
    "references",
    "tests",
    "events",
    "distinctions",
    "misconceptions",
    "clusters",
    "policies",
    "visuals",
    "indexes",
    "context_packs",
    "ai_runs",
]

SESSION_SECTIONS = [
    "Started with",
    "AI used for",
    "Student outputs",
    "New claims",
    "New positioning decisions",
    "Unresolved",
    "Next actions",
]

TEMPLATES: dict[str, str] = {
    "goal.yaml": """id: goal_example
title: Example learning goal
main_goal: What disciplinary capability are you building?
stage_goal: What should improve next?
transfer_goal: Where should this knowledge transfer?
external_goal: What outside deadline or use matters?
active: true
priority_topics: []
created_at:
updated_at:
""",
    "position.yaml": """id: position_example
goal_id: goal_example
policy_id:
knowledge_point: density_matrix
position: B_knowledge_positioning
tool_role: core_tool
reason: Why this depth is enough for the current goal.
confidence: medium
epistemic_status: learning_strategy
revisit_when: []
record_strength: light
record_intensity: light
internalization_level: none
created_at:
updated_at:
""",
    "claim.yaml": """id: claim_example
goal_id: goal_example
text: Student-generated claim.
context: Where this claim came from.
type: hypothesis
status: unverified
epistemic_status: speculation
strict_part: ""
caveat: ""
counterexample_or_boundary: ""
next_action: Verify with AI or source.
record_intensity: light
created_at:
updated_at:
""",
    "derivation.yaml": """id: derivation_example
goal_id: goal_example
topic: nondegenerate_perturbation_theory
importance: core_tool
status: not_started
result_to_trust: Result or formula to reconstruct.
user_derived_steps: []
ai_hinted_steps: []
not_yet_trusted: []
next_action: Start from definitions.
record_intensity: light
created_at:
updated_at:
""",
    "reference.yaml": """id: reference_example
goal_id: goal_example
title: Durable source title
authors_or_source: Author or source
reference_type: textbook
path_or_url: path/or/url
topics: []
relevance_to_goal: Why this source matters for the current goal.
usage_stage: initial_map
reading_status: unread
notes: ""
created_at:
updated_at:
""",
    "policy.yaml": """id: policy_example
goal_id: goal_example
title: Example classification policy
description: A/B/C is a dynamic classification grammar for this goal, not a fixed map.
a_zone_criteria: []
b_zone_criteria: []
c_zone_criteria: []
core_tool_criteria: []
non_core_tool_criteria: []
test_mode_criteria: []
upgrade_triggers: []
downgrade_triggers: []
revisit_triggers: []
examples_optional: []
created_at:
updated_at:
""",
    "visual.yaml": """id: visual_example
goal_id: goal_example
topic: density_matrix
title: Durable visual metadata entry
visual_type: reliable_web_image
source_priority: reliable_web
source_url_or_path: ""
source_detail: ""
reliability: medium
usage: explanation
why_needed: Why this visual helps the learner's current state.
related_record_ids: []
copyright_note: Store metadata and usage purpose, not large media by default.
created_at:
updated_at:
""",
    "session.md": """---
id: session_example
goal_id: goal_example
topic: perturbation_theory
mode: derivation
learning_state:
methods_used: []
references_used: []
provisional_understanding: ""
test_mode_triggered: false
references_added: []
created_at:
---

## Started with

## AI used for

## Student outputs

## New claims

## New positioning decisions

## Unresolved

## Next actions
""",
    "test.yaml": """id: test_example
goal_id: goal_example
topic: perturbation_theory
position_id:
test_type: mixed
status: planned
internalization_target: A3
prompt: ""
learner_answer:
feedback:
created_at:
updated_at:
next_retest_at:
""",
    "distinction.yaml": """id: distinction_example
goal_id: goal_example
title: superposition vs entanglement
concepts:
- superposition_state
- entangled_state
confusion_statement: Learner-specific confusion to distinguish.
shared_features: []
distinguishing_criteria: []
minimal_examples: []
boundary_cases: []
common_misconceptions: []
status: needs_distinction
internalization_target: none
record_intensity: light
first_confused_at:
last_confused_at:
last_distinguished_at:
next_distinction_test_at:
confusion_count: 0
related_claim_ids: []
related_test_ids: []
related_session_ids: []
created_at:
updated_at:
first_seen_at:
last_touched_at:
last_reviewed_at:
last_tested_at:
next_review_at:
next_action: ""
""",
    "misconception.yaml": """id: misconception_example
goal_id: goal_example
statement: A learner's wrong statement.
why_wrong: Why this statement fails.
corrected_view: Short corrected view.
related_topics: []
severity: important
status: active
first_seen_at:
last_seen_at:
corrected_at:
recurrence_count: 0
related_claim_ids: []
related_distinction_ids: []
related_session_ids: []
created_at:
updated_at:
last_touched_at:
last_reviewed_at:
last_tested_at:
next_review_at:
next_action: ""
""",
    "cluster.yaml": """id: cluster_example
goal_id: goal_example
title: Concepts that should be learned together
core_question: Why are these concepts grouped for this learner?
concepts: []
current_status: provisional
reason: Learning-state grouping only, not a knowledge graph.
related_distinction_ids: []
related_position_ids: []
related_session_ids: []
created_at:
updated_at:
first_seen_at:
last_touched_at:
last_reviewed_at:
last_tested_at:
next_review_at:
next_action: ""
""",
    "review.md": """---
id: review_example
kind: weekly
created_at:
---

# Weekly Review

## Recent Sessions

## Unverified Claims

## Derivations Not Trusted

## Positioning Revisit Triggers

## Suggested Socratic Drill Topics

## Suggested Next Actions
""",
}

MODEL_DIRECTORIES: dict[str, type[BaseModel]] = {
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


def project_root(path: Path | str = ".") -> Path:
    return Path(path).expanduser().resolve()


def init_project(path: Path | str) -> Path:
    root = project_root(path)
    (root / "src" / "ailearn").mkdir(parents=True, exist_ok=True)
    for directory in DATA_DIRS:
        (root / "data" / directory).mkdir(parents=True, exist_ok=True)
    (root / "templates").mkdir(parents=True, exist_ok=True)
    for filename, content in TEMPLATES.items():
        template_path = root / "templates" / filename
        if not template_path.exists():
            template_path.write_text(content, encoding="utf-8")
    return root


def save_yaml_model(path: Path | str, model: BaseModel) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json")
    output.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return output


def load_yaml_model(path: Path | str, model_cls: type[ModelT]) -> ModelT:
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return model_cls.model_validate(data)


def save_record(root: Path | str, directory: str, model: BaseModel) -> Path:
    record_id = getattr(model, "id")
    return save_yaml_model(Path(root) / "data" / directory / f"{record_id}.yaml", model)


def list_yaml_records(root: Path | str, directory: str, model_cls: type[ModelT]) -> list[ModelT]:
    data_dir = Path(root) / "data" / directory
    records: list[ModelT] = []
    for path in sorted(data_dir.glob("*.yaml")):
        records.append(load_yaml_model(path, model_cls))
    return records


def load_goals(root: Path | str) -> list[Goal]:
    return list_yaml_records(root, "goals", Goal)


def active_goal(root: Path | str) -> Goal | None:
    goals = [goal for goal in load_goals(root) if goal.active]
    if not goals:
        return None
    return sorted(goals, key=lambda goal: goal.updated_at, reverse=True)[0]


def session_markdown(session: SessionFootprint, body: dict[str, str] | None = None) -> str:
    body = body or {}
    frontmatter = yaml.safe_dump(
        session.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    sections: list[str] = ["---", frontmatter.rstrip(), "---", ""]
    for section in SESSION_SECTIONS:
        content = body.get(section, "").strip()
        sections.extend([f"## {section}", "", content, ""])
    return "\n".join(sections).rstrip() + "\n"


def save_session(path: Path | str, session: SessionFootprint, body: dict[str, str] | None = None) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(session_markdown(session, body), encoding="utf-8")
    return output


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata = yaml.safe_load(parts[1]) or {}
    return metadata, parts[2].lstrip()


def _parse_markdown_sections(markdown: str) -> dict[str, str]:
    body: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1)
            body[current] = []
            continue
        if current is not None:
            body[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in body.items()}


def load_session(path: Path | str) -> tuple[SessionFootprint, dict[str, str]]:
    text = Path(path).read_text(encoding="utf-8")
    metadata, markdown = _split_frontmatter(text)
    session = SessionFootprint.model_validate(metadata)
    return session, _parse_markdown_sections(markdown)


def list_sessions(root: Path | str) -> list[tuple[Path, SessionFootprint, dict[str, str]]]:
    sessions: list[tuple[Path, SessionFootprint, dict[str, str]]] = []
    for path in sorted((Path(root) / "data" / "sessions").glob("*.md")):
        session, body = load_session(path)
        sessions.append((path, session, body))
    return sessions


def copy_research_import(root: Path | str, source: Path | str, timestamp: str) -> Path:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Deep Research import not found: {source_path}")
    output_name = f"{timestamp}-{source_path.name}"
    output_path = Path(root) / "data" / "research_imports" / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)
    return output_path


def research_imports(root: Path | str) -> list[Path]:
    return sorted((Path(root) / "data" / "research_imports").glob("*.md"))


def find_research_import(root: Path | str, import_id: str) -> Path:
    imports = research_imports(root)
    for path in imports:
        if import_id in {path.name, path.stem} or path.name.startswith(import_id):
            return path
    raise FileNotFoundError(f"Research import not found: {import_id}")

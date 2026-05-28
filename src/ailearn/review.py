from __future__ import annotations

from pathlib import Path

from .ids import new_id, now_utc
from .method_router import recommend_methods
from .models import (
    ClaimRecord,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    TestRecord,
)
from .status import suggest_next_actions
from .storage import (
    list_sessions,
    list_yaml_records,
)
from .test_mode import suggest_tests


def due_review_items(root: Path | str = ".") -> list[str]:
    base = Path(root)
    current = now_utc()
    items: list[str] = []
    for position in list_yaml_records(base, "positioning", PositionDecision):
        if position.next_review_at and position.next_review_at <= current:
            items.append(f"{position.id}: review due for {position.knowledge_point}")
    for claim in list_yaml_records(base, "claims", ClaimRecord):
        if claim.next_recheck_at and claim.next_recheck_at <= current:
            items.append(f"{claim.id}: claim recheck due for {claim.text}")
        elif claim.next_review_at and claim.next_review_at <= current:
            items.append(f"{claim.id}: review due for claim {claim.text}")
    for derivation in list_yaml_records(base, "derivations", DerivationRecord):
        if derivation.next_rederive_at and derivation.next_rederive_at <= current:
            items.append(f"{derivation.id}: re-derive due for {derivation.topic}")
        elif derivation.next_review_at and derivation.next_review_at <= current:
            items.append(f"{derivation.id}: review due for derivation {derivation.topic}")
    for test in list_yaml_records(base, "tests", TestRecord):
        if test.next_retest_at and test.next_retest_at <= current:
            items.append(f"{test.id}: retest due for {test.topic}")
    for distinction in list_yaml_records(base, "distinctions", DistinctionRecord):
        if distinction.next_distinction_test_at and distinction.next_distinction_test_at <= current:
            items.append(f"{distinction.id}: distinction test due for {distinction.title}")
        elif distinction.next_review_at and distinction.next_review_at <= current:
            items.append(f"{distinction.id}: review due for distinction {distinction.title}")
    for misconception in list_yaml_records(base, "misconceptions", MisconceptionRecord):
        if misconception.status == "recurring" or misconception.recurrence_count >= 2:
            items.append(f"{misconception.id}: recurring misconception: {misconception.statement}")
        elif misconception.next_review_at and misconception.next_review_at <= current:
            items.append(f"{misconception.id}: review due for misconception {misconception.statement}")
    return items


def _line_or_none(items: list[str]) -> list[str]:
    return items if items else ["- None recorded."]


def _format_lines(items: list[str]) -> str:
    return "\n".join(_line_or_none(items))


def generate_weekly_review(root: Path | str = ".") -> Path:
    base = Path(root)
    now = now_utc()
    review_id = new_id("review")

    sessions = list_sessions(base)
    goals = list_yaml_records(base, "goals", Goal)
    references = list_yaml_records(base, "references", ReferenceRecord)
    claims = list_yaml_records(base, "claims", ClaimRecord)
    derivations = list_yaml_records(base, "derivations", DerivationRecord)
    positions = list_yaml_records(base, "positioning", PositionDecision)
    tests = list_yaml_records(base, "tests", TestRecord)
    distinctions = list_yaml_records(base, "distinctions", DistinctionRecord)
    misconceptions = list_yaml_records(base, "misconceptions", MisconceptionRecord)

    recent_sessions = [
        f"- {session.created_at.date()}: {session.topic} ({session.mode})"
        for _, session, _ in sorted(sessions, key=lambda item: item[1].created_at, reverse=True)
    ]
    unverified_claims = [
        f"- {claim.id}: {claim.text} [status={claim.status}, epistemic={claim.epistemic_status}, intensity={claim.record_intensity}]"
        for claim in claims
        if claim.status in {"unverified", "open_question"}
    ]
    weak_claims = [
        f"- {claim.id}: {claim.text} [status={claim.status}] Boundary: {claim.counterexample_or_boundary or 'not recorded'}"
        for claim in claims
        if claim.status in {"misleading", "partially_correct", "wrong"}
    ]
    untrusted_derivations = [
        f"- {derivation.topic} [status={derivation.status}, importance={derivation.importance}, intensity={derivation.record_intensity}] Next: {derivation.next_action or 'not recorded'}"
        for derivation in derivations
        if derivation.status != "trusted"
    ]
    revisit_positions = [
        f"- {position.knowledge_point} [{position.position}, {position.tool_role}] Revisit: {', '.join(position.revisit_when)}"
        for position in positions
        if position.revisit_when
    ]

    new_references = [
        f"- {reference.title} [{reference.reference_type}, {reference.usage_stage}, {reference.reading_status}] Topics: {', '.join(reference.topics) or 'not recorded'}"
        for reference in sorted(references, key=lambda ref: ref.created_at, reverse=True)
    ]
    used_reference_ids = {
        reference_id
        for _, session, _ in sessions
        for reference_id in session.references_used
    }
    references_used = [
        f"- {reference.title} ({reference.id})"
        for reference in references
        if reference.id in used_reference_ids
    ]
    goals_needing_refinement = [
        f"- {goal.title}: missing one or more goal fields."
        for goal in goals
        if not all([goal.main_goal, goal.stage_goal, goal.transfer_goal, goal.external_goal])
    ]
    learning_states = [
        str(session.learning_state)
        for _, session, _ in sessions
        if session.learning_state is not None
    ]
    method_recommendations = []
    for state in sorted(set(learning_states)):
        recommendation = recommend_methods(state)
        method_recommendations.append(f"- {state}: {', '.join(recommendation.actions)}")
    test_suggestions = [f"- {suggestion}" for suggestion in suggest_tests(base)]
    a_progress = [
        f"- {position.knowledge_point}: {position.internalization_level} [{position.position}, intensity={position.record_intensity}]"
        for position in positions
        if position.internalization_level in {"A0", "A1", "A2", "A3"}
    ]
    test_attention = [
        f"- {record.topic}: {record.status} -> target {record.internalization_target}"
        for record in tests
        if record.status in {"planned", "failed", "needs_retest"}
    ]
    distinction_attention = [
        f"- {record.id}: {record.title} [status={record.status}, target={record.internalization_target}, confusion_count={record.confusion_count}] Next: {record.next_action or 'run distinction prompt/test'}"
        for record in distinctions
        if record.status in {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}
    ]
    repeated_misconceptions = [
        f"- {record.id}: {record.statement} [status={record.status}, recurrence_count={record.recurrence_count}, severity={record.severity}] Next: {record.next_action or 'run misconception correction prompt'}"
        for record in misconceptions
        if record.status == "recurring" or record.recurrence_count >= 2
    ]
    visual_suggestions = [
        f"- {record.title}: persistent distinction/confusion may benefit from a figure, animation, or schematic."
        for record in distinctions
        if record.status in {"needs_distinction", "needs_test", "needs_retest"} and (record.confusion_count >= 2 or record.record_intensity in {"medium", "heavy"})
    ]
    visual_suggestions.extend(
        f"- {record.statement}: recurring misconception may benefit from a visual explanation or boundary-case diagram."
        for record in misconceptions
        if record.status == "recurring" or record.recurrence_count >= 2
    )
    visual_suggestions.extend(
        f"- {record.topic}: if the derivation has geometric or dynamic structure, consider linking a visual resource."
        for record in derivations
        if record.status != "trusted" and record.record_intensity in {"medium", "heavy"}
    )
    visual_suggestions.extend(
        f"- {reference.title}: if this source has important figures, link them as VisualResourceRecord metadata."
        for reference in references
        if reference.usage_stage == "core_learning"
    )
    due_items = [f"- {item}" for item in due_review_items(base)]

    drill_topics = sorted(
        {
            *(claim.text for claim in claims if claim.status in {"unverified", "partially_correct", "misleading", "wrong"}),
            *(derivation.topic for derivation in derivations if derivation.status != "trusted"),
            *(position.knowledge_point for position in positions if position.revisit_when),
            *(distinction.title for distinction in distinctions if distinction.status in {"needs_distinction", "needs_test", "needs_retest"}),
            *(misconception.statement for misconception in misconceptions if misconception.status in {"active", "recurring"}),
        }
    )
    drill_lines = [f"- {topic}" for topic in drill_topics]

    next_actions = sorted(
        {
            *(claim.next_action for claim in claims if claim.next_action and claim.status != "verified"),
            *(derivation.next_action for derivation in derivations if derivation.next_action and derivation.status != "trusted"),
            "Run Socratic drill on one unresolved or weak topic." if drill_topics else "",
        }
        - {""}
    )
    next_action_lines = [f"- {action}" for action in next_actions]
    top_three = [f"- {action}" for action in suggest_next_actions(base, limit=3)]

    content = f"""---
id: {review_id}
kind: weekly
created_at: {now.isoformat()}
---

# Weekly Review - {now.date()}

## Recent Sessions

{_format_lines(recent_sessions)}

## New References Added

{_format_lines(new_references)}

## References Used

{_format_lines(references_used)}

## Goals Needing Refinement

{_format_lines(goals_needing_refinement)}

## Unverified Claims

{_format_lines(unverified_claims)}

## Misleading Or Partially Correct Claims

{_format_lines(weak_claims)}

## Derivations Not Trusted

{_format_lines(untrusted_derivations)}

## Positioning Revisit Triggers

{_format_lines(revisit_positions)}

## A-Level Internalization Progress

{_format_lines(a_progress)}

## Topics Ready For Test Mode

{_format_lines(test_suggestions)}

## Tests Needing Attention

{_format_lines(test_attention)}

## Distinctions Needing Tests

{_format_lines(distinction_attention)}

## Repeated Misconceptions

{_format_lines(repeated_misconceptions)}

## Visual Support Suggestions

{_format_lines(visual_suggestions)}

## Records With Due Reviews

{_format_lines(due_items)}

## Unresolved Learning States

{_format_lines([f"- {state}" for state in learning_states])}

## Suggested Learning Methods

{_format_lines(method_recommendations)}

## Suggested Socratic Drill Topics

{_format_lines(drill_lines)}

## Suggested Next Actions

{_format_lines(next_action_lines)}

## Next Week Top 3 Actions

{_format_lines(top_three)}
"""
    output = base / "data" / "reviews" / f"{now.strftime('%Y%m%d')}-{review_id}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output

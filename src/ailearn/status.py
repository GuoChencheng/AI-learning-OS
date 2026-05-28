from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .method_router import recommend_methods
from .models import (
    ClaimRecord,
    DerivationRecord,
    DistinctionRecord,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    TestRecord,
)
from .storage import active_goal, list_sessions, list_yaml_records
from .test_mode import suggest_tests
from .ids import now_utc


@dataclass
class ProjectStatus:
    active_goal_title: str = "None"
    references_count: int = 0
    unverified_claims: int = 0
    weak_claims: int = 0
    derivations_needing_trust: int = 0
    a_level_counts: dict[str, int] = field(default_factory=dict)
    tests_attention: int = 0
    distinctions_attention: int = 0
    recurring_misconceptions: int = 0
    due_reviews: int = 0
    recent_sessions: list[str] = field(default_factory=list)
    unresolved_learning_states: list[str] = field(default_factory=list)


def project_status(root: Path | str = ".") -> ProjectStatus:
    base = Path(root)
    goal = active_goal(base)
    references = list_yaml_records(base, "references", ReferenceRecord)
    claims = list_yaml_records(base, "claims", ClaimRecord)
    derivations = list_yaml_records(base, "derivations", DerivationRecord)
    positions = list_yaml_records(base, "positioning", PositionDecision)
    tests = list_yaml_records(base, "tests", TestRecord)
    distinctions = list_yaml_records(base, "distinctions", DistinctionRecord)
    misconceptions = list_yaml_records(base, "misconceptions", MisconceptionRecord)
    sessions = list_sessions(base)
    if goal is not None:
        references = [record for record in references if record.goal_id == goal.id]
        claims = [record for record in claims if record.goal_id == goal.id]
        derivations = [record for record in derivations if record.goal_id == goal.id]
        positions = [record for record in positions if record.goal_id == goal.id]
        tests = [record for record in tests if record.goal_id == goal.id]
        distinctions = [record for record in distinctions if record.goal_id == goal.id]
        misconceptions = [record for record in misconceptions if record.goal_id == goal.id]
        sessions = [item for item in sessions if item[1].goal_id == goal.id]

    a_counts = {level: 0 for level in ["A0", "A1", "A2", "A3", "A4"]}
    for position in positions:
        if position.internalization_level in a_counts:
            a_counts[str(position.internalization_level)] += 1

    attention_statuses = {"planned", "failed", "needs_retest"}
    distinction_attention_statuses = {"needs_distinction", "partially_clear", "needs_test", "needs_retest"}
    learning_states = [
        str(session.learning_state)
        for _, session, _ in sessions
        if session.learning_state is not None
    ]
    current = now_utc()
    due_reviews = 0
    for record in [*positions, *claims, *derivations, *tests, *distinctions, *misconceptions]:
        next_review = getattr(record, "next_review_at", None)
        if next_review and next_review <= current:
            due_reviews += 1

    return ProjectStatus(
        active_goal_title=goal.title if goal else "None",
        references_count=len(references),
        unverified_claims=sum(1 for claim in claims if claim.status in {"unverified", "open_question"}),
        weak_claims=sum(1 for claim in claims if claim.status in {"partially_correct", "misleading", "wrong"}),
        derivations_needing_trust=sum(1 for derivation in derivations if derivation.status != "trusted"),
        a_level_counts=a_counts,
        tests_attention=sum(1 for test in tests if test.status in attention_statuses),
        distinctions_attention=sum(1 for distinction in distinctions if distinction.status in distinction_attention_statuses),
        recurring_misconceptions=sum(1 for misconception in misconceptions if misconception.status == "recurring" or misconception.recurrence_count >= 2),
        due_reviews=due_reviews,
        recent_sessions=[session.topic for _, session, _ in sorted(sessions, key=lambda item: item[1].created_at, reverse=True)[:5]],
        unresolved_learning_states=learning_states[-5:],
    )


def render_status(status: ProjectStatus) -> str:
    sessions = ", ".join(status.recent_sessions) if status.recent_sessions else "None"
    states = ", ".join(status.unresolved_learning_states) if status.unresolved_learning_states else "None"
    a_levels = ", ".join(f"{level}: {count}" for level, count in status.a_level_counts.items())
    return "\n".join(
        [
            f"Active goal: {status.active_goal_title}",
            f"References: {status.references_count}",
            f"Unverified/open claims: {status.unverified_claims}",
            f"Partially correct/misleading/wrong claims: {status.weak_claims}",
            f"Derivations needing trust: {status.derivations_needing_trust}",
            f"A-level internalization: {a_levels}",
            f"Tests planned/failed/needs_retest: {status.tests_attention}",
            f"Distinctions needing attention: {status.distinctions_attention}",
            f"Recurring misconceptions: {status.recurring_misconceptions}",
            f"Records with review due: {status.due_reviews}",
            f"Recent sessions: {sessions}",
            f"Unresolved learning states: {states}",
        ]
    )


def suggest_next_actions(root: Path | str = ".", limit: int = 5) -> list[str]:
    base = Path(root)
    goal = active_goal(base)
    claims = list_yaml_records(base, "claims", ClaimRecord)
    derivations = list_yaml_records(base, "derivations", DerivationRecord)
    positions = list_yaml_records(base, "positioning", PositionDecision)
    references = list_yaml_records(base, "references", ReferenceRecord)
    tests = list_yaml_records(base, "tests", TestRecord)
    distinctions = list_yaml_records(base, "distinctions", DistinctionRecord)
    misconceptions = list_yaml_records(base, "misconceptions", MisconceptionRecord)
    sessions = list_sessions(base)
    if goal is not None:
        claims = [record for record in claims if record.goal_id == goal.id]
        derivations = [record for record in derivations if record.goal_id == goal.id]
        positions = [record for record in positions if record.goal_id == goal.id]
        references = [record for record in references if record.goal_id == goal.id]
        tests = [record for record in tests if record.goal_id == goal.id]
        distinctions = [record for record in distinctions if record.goal_id == goal.id]
        misconceptions = [record for record in misconceptions if record.goal_id == goal.id]
        sessions = [item for item in sessions if item[1].goal_id == goal.id]

    actions: list[str] = []

    def add_once(text: str) -> None:
        if len(actions) < limit and text not in actions:
            actions.append(text)

    handled_claim_ids: set[str] = set()
    for claim in claims:
        if claim.status in {"unverified", "open_question"} and claim.record_intensity in {"medium", "heavy"}:
            add_once(f"Verify high/medium/heavy claim: {claim.text}")
            handled_claim_ids.add(claim.id)
    for claim in claims:
        if claim.status in {"unverified", "open_question"} and claim.id not in handled_claim_ids:
            add_once(f"Verify claim: {claim.text}")

    for derivation in derivations:
        if derivation.status != "trusted":
            add_once(f"Run derivation trust work for {derivation.topic}")

    for suggestion in suggest_tests(base):
        add_once(f"Run test mode: {suggestion}")

    current = now_utc()
    for distinction in distinctions:
        visual_needed = distinction.confusion_count >= 2 or distinction.record_intensity in {"medium", "heavy"}
        if distinction.status in {"needs_distinction", "needs_test", "needs_retest"}:
            add_once(f"Run distinction test for {distinction.title}")
            if visual_needed:
                add_once(f"Consider visual explanation for persistent distinction: {distinction.title}")
        if distinction.next_distinction_test_at and distinction.next_distinction_test_at <= current:
            if visual_needed:
                add_once(f"Distinction test due with visual support: {distinction.title}")
            else:
                add_once(f"Distinction test due: {distinction.title}")

    for misconception in misconceptions:
        if misconception.status == "recurring" or misconception.recurrence_count >= 2:
            add_once(f"Review recurring misconception: {misconception.statement}")
            add_once(f"Consider visual explanation for recurring misconception: {misconception.statement}")

    for record in [*positions, *claims, *derivations, *tests, *distinctions, *misconceptions]:
        next_review = getattr(record, "next_review_at", None)
        if next_review and next_review <= current:
            label = getattr(record, "knowledge_point", None) or getattr(record, "topic", None) or getattr(record, "title", None) or getattr(record, "text", None) or getattr(record, "statement", getattr(record, "id", "record"))
            add_once(f"Review due: {label}")

    for derivation in derivations:
        if derivation.next_rederive_at and derivation.next_rederive_at <= current:
            add_once(f"Re-derive due: {derivation.topic}")

    for test in tests:
        if test.next_retest_at and test.next_retest_at <= current:
            add_once(f"Delayed retrieval or retest due: {test.topic}")

    for position in positions:
        if position.revisit_when:
            add_once(f"Revisit positioning for {position.knowledge_point}: {', '.join(position.revisit_when)}")

    if not references:
        add_once("Add or review references for the active goal.")
    elif any(reference.reading_status == "unread" for reference in references):
        add_once("Review unread references and decide whether they are core or optional.")

    if len(claims) + len(derivations) + len(positions) > 20:
        add_once("Clarify or restructure the goal; too many active items may be chaotic.")

    unclear_states = {"totally_unclear", "unknown_next_step", "too_much_material"}
    session_states = [str(session.learning_state) for _, session, _ in sessions if session.learning_state is not None]
    if any(state in unclear_states for state in session_states):
        state = next(state for state in session_states if state in unclear_states)
        recommendation = recommend_methods(state)
        add_once(f"Generate method-router prompt for {state}: {', '.join(recommendation.actions)}")

    return actions[:limit]

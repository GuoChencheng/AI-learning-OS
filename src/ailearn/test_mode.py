from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import ClaimRecord, DerivationRecord, Goal, PositionDecision, TestRecord
from .prompts import test_record_prompt as _test_record_prompt
from .storage import list_sessions, list_yaml_records


def test_record_prompt(goal: Goal, test_record: TestRecord) -> str:
    return _test_record_prompt(goal, test_record)


test_record_prompt.__test__ = False


def suggest_tests(root: Path | str = ".") -> list[str]:
    base = Path(root)
    positions = list_yaml_records(base, "positioning", PositionDecision)
    derivations = list_yaml_records(base, "derivations", DerivationRecord)
    claims = list_yaml_records(base, "claims", ClaimRecord)
    tests = list_yaml_records(base, "tests", TestRecord)
    sessions = list_sessions(base)

    tested_topics = {record.topic for record in tests}
    tested_positions = {record.position_id for record in tests if record.position_id}
    suggestions: list[str] = []

    def add_once(text: str) -> None:
        if text not in suggestions:
            suggestions.append(text)

    for position in positions:
        if position.position == "A_no_ai_internalization" and position.id not in tested_positions:
            add_once(f"Create test mode for A-level item: {position.knowledge_point}")
        if position.internalization_level in {"A0", "A1"}:
            add_once(f"Progress internalization test for {position.knowledge_point} ({position.internalization_level})")

    for derivation in derivations:
        if derivation.record_intensity == "heavy" and derivation.status != "trusted":
            add_once(f"Test heavy untrusted derivation: {derivation.topic}")

    topic_counts = Counter(session.topic for _, session, _ in sessions)
    for topic, count in topic_counts.items():
        if count >= 2 and topic not in tested_topics:
            add_once(f"Repeated session topic without test: {topic}")

    for claim in claims:
        if claim.status == "verified" and claim.record_intensity in {"medium", "heavy"}:
            add_once(f"Internalize verified claim: {claim.text}")

    return suggestions

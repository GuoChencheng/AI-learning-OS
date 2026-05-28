# Data Model

`ai-learning-os` separates learning state into three layers.

## Snapshot Records

YAML records under `data/` store current state only. They should remain short enough to read and edit directly.

Examples:
- `PositionDecision`: current A/B/C positioning relative to a goal.
- `ClassificationPolicy`: current goal-derived A/B/C criteria and triggers.
- `ClaimRecord`: current verification and epistemic status.
- `DerivationRecord`: current derivation trust state.
- `DistinctionRecord`: current learner-specific adjacent-concept confusion.
- `MisconceptionRecord`: current state of a wrong or recurring idea.
- `VisualResourceRecord`: visual metadata and learning purpose.

Do not append long histories to these YAML files.

## Event Logs

Historical state changes are append-only JSONL records under:

```text
data/events/YYYY-MM.jsonl
```

Each event is compact and structured:
- event type;
- target type and id;
- optional goal id;
- short summary;
- optional before/after snapshots;
- source;
- related record ids.

Important event types include `record_created`, `record_updated`, `position_changed`, `claim_status_changed`, `distinction_status_changed`, `confusion_recorded`, `delayed_retrieval_failed`, `review_scheduled`, and `review_completed`.

## Session Logs

Session Markdown files keep the raw learning footprint:
- what the learner started with;
- what AI was used for;
- student outputs;
- unresolved issues;
- references used;
- confused topics;
- next actions.

Sessions can be messier than snapshot records.

## DistinctionRecord

Use a DistinctionRecord when the learner’s difficulty is “I cannot distinguish X from Y.”

This is not a knowledge-graph edge. It records a learner-specific distinction problem: shared features, distinguishing criteria, examples, boundary cases, misconceptions, status, target internalization level, and next test timing.

## MisconceptionRecord

Use a MisconceptionRecord when the learner has a clearly wrong statement.

It stores the wrong statement, why it is wrong, a corrected view, related topics, severity, recurrence count, current status, and next action. If it recurs, increment recurrence count and append an event.

## ClassificationPolicy

Use a ClassificationPolicy to store the current A/B/C language derived from a goal. It records criteria for A/B/C zones, core tools, non-core tools, test mode, upgrade triggers, downgrade triggers, revisit triggers, and optional examples.

A policy is not a static field map. PositionDecision may reference `policy_id` when a knowledge point was classified against a specific current policy.

## VisualResourceRecord

Use a VisualResourceRecord when a concept, distinction, derivation, misconception, test, review, or reference needs visual support.

It stores metadata only:
- visual type;
- source priority;
- URL/path or source detail;
- reliability;
- usage purpose;
- why the visual is needed;
- related record ids;
- copyright note.

Do not store large media files by default. Literature figures are preferred for paper learning; AI-generated schematics must be labeled illustrative and not evidence.

## Derived Indexes And Context Packs

`data/indexes/` contains derived summaries:
- `active_goal_summary.md`
- `open_loops.md`
- `recent_activity.md`
- `reference_index.yaml`
- `record_manifest.jsonl`
- `topic_index.yaml`

These are retrieval aids, not sources of truth. Regenerate them from local records with `learn index refresh`.

`data/context_packs/` contains task-specific Markdown context packs for AI agents. They should stay compact and should not blindly include all sessions, references, or Deep Research imports.

## Temporal Fields

Learning-state records may include:
- `first_seen_at`
- `last_touched_at`
- `last_reviewed_at`
- `last_tested_at`
- `next_review_at`

Claims add `last_checked_at`, `verified_at`, and `next_recheck_at`.

Derivations add `first_attempted_at`, `last_attempted_at`, `trusted_at`, `last_rederived_at`, and `next_rederive_at`.

Tests add `attempted_at`, `passed_at`, `failed_at`, `next_retest_at`, and optional `test_interval_days`.

Timestamps are timezone-aware. Internal event timestamps use UTC plus a user-facing local timestamp, defaulting to `Asia/Shanghai`.

## Review Scheduling

The deterministic review logic flags:
- records with due `next_review_at`;
- claims with due `next_recheck_at`;
- tests with due `next_retest_at`;
- derivations with due `next_rederive_at`;
- distinctions with due `next_distinction_test_at`;
- recurring misconceptions.

Temporal traces help distinguish short-term confusion, long-term forgetting, repeated misconception, and ordinary review due.

## Object Routing

- “What is X?” -> PositionDecision.
- “What is the difference between X and Y?” -> DistinctionRecord.
- “I thought X was Y.” -> MisconceptionRecord.
- “X, Y, Z always appear together.” -> ConceptClusterRecord.
- “I think X is related to Y.” -> ClaimRecord.
- “I need to trust this formula/result.” -> DerivationRecord.
- “I think I have learned this.” -> TestRecord.
- “Which A/B/C criteria should guide this goal?” -> ClassificationPolicy.
- “This needs a diagram/video/figure.” -> VisualResourceRecord.

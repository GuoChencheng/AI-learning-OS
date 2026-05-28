# AI Context Loading Protocol

The goal is to prevent AI agents from reading all local data by default. Agents should identify the task type, then load only the context needed for that task.

## Context Layers

1. Always-readable methodology: `AGENTS.md`, `docs/core_methodology.md`, and this protocol.
2. Derived indexes: `data/indexes/active_goal_summary.md`, `open_loops.md`, `recent_activity.md`, `reference_index.yaml`, `record_manifest.jsonl`, and `topic_index.yaml`.
3. Primary record: the claim, derivation, position, distinction, misconception, test, reference, or policy being worked on.
4. Related records: selected through the manifest and topic index.
5. Compact timelines: selected JSONL events for the target record.
6. Raw sessions, references, and Deep Research reports: read only when the task clearly requires them.

Indexes are summaries, not sources of truth. Source records remain YAML, Markdown, and JSONL files.

## Task Types

Supported task types include:

- `goal_intake`
- `deep_research`
- `extract_references`
- `positioning`
- `verify_claim`
- `derivation_guidance`
- `distinction`
- `misconception`
- `test_topic`
- `weekly_review`
- `temporal_review`
- `method_routing`
- `reference_review`

## What To Read

For `verify_claim`, read the active goal, the claim record, linked or topic-related distinctions/misconceptions/positions, compact claim timeline, and reference metadata if relevant. Do not read all sessions or all references.

For `derivation_guidance`, read the active goal, derivation record, related claims/tests, compact derivation timeline, and reference metadata if the record points to sources.

For `positioning`, read the active goal, classification policy if present, existing position record if any, topic-index neighbors, recent related sessions, and reference metadata. A/B/C decisions are learning strategy judgments.

For `distinction`, read the active goal, distinction record, related misconceptions, related tests, and compact timeline.

For `misconception`, read the active goal, misconception record, related claims/distinctions, and recurrence timeline.

For `test_topic`, read the active goal, position records for the topic, claims, derivations, distinctions, misconceptions, previous tests, and compact recent sessions.

For `weekly_review`, read the active goal, `open_loops.md`, `recent_activity.md`, due review/test items, and compact manifest lists. Do not read raw full references.

For `reference_review`, read reference metadata and local notes. Read full reference content only when explicitly requested.

## What Not To Read

Do not read all references by default. Do not read all Deep Research imports by default. Do not read all session bodies by default. Do not treat references as a knowledge database. Do not treat Deep Research as final truth.

## Context Budgets

Small: methodology summary, active goal, primary record, and top five related records.

Medium: small plus compact timeline, up to ten related records, and reference metadata.

Large: medium plus selected session excerpts or selected research excerpts when the task requires them. Large still does not mean unlimited raw data.

## Context Packs

Use:

```bash
learn index refresh
learn context build --task verify_claim --id claim_example
learn context build --task test_topic --topic perturbation_theory --budget small
```

Context packs are Markdown files under `data/context_packs/`. They are task-specific loading plans and evidence summaries, not source records.

## Provider Runs

Optional provider-backed runs must use explicit prompt files, generated prompts, or context packs. Do not send all local data by default.

Before a connected-mode run, show a compact preview: provider, model, context size, detected record ids, detected reference ids, whether raw sessions are included, and whether raw references are included.

AI responses are artifacts under `data/ai_runs/`, not source-of-truth records. The learner must review and explicitly apply any accepted changes.

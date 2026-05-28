# AGENTS.md

## Project identity

This project is an AI-native learning workflow manager.

It is not:
- a knowledge graph app;
- an encyclopedia;
- a note summarizer;
- a frontend-first or hosted web app.

The system stores learning state, not world knowledge.

## Required AI-agent startup protocol

Before working on learner data, read:

1. `AGENTS.md`
2. `docs/core_methodology.md`
3. `docs/ai_context_protocol.md`

Then identify the task type before reading data. Prefer `learn index refresh` and `learn context build --task ...` over opening all local records. Do not read all sessions, all references, or all Deep Research reports by default.

For UI work, also read:

4. `docs/ui_design.md`
5. `docs/ui_principles.md`
6. `skills/ui_simplicity/SKILL.md`

## Core philosophy

AI can dynamically reason about knowledge relations at runtime.
Therefore, the local system should not duplicate a static world knowledge graph.

The local system should preserve:
- learning goals;
- classification policies derived from goals;
- dynamic positioning decisions;
- student-generated claims;
- epistemic verification status;
- derivation/trust-building records;
- adjacent-concept distinction records;
- recurring misconception records;
- compact temporal event logs;
- lightweight session footprints;
- durable source references;
- visual resource metadata;
- method routing decisions;
- test-mode records;
- weekly reviews.

## Workflow

Goal Intake
-> Deep Research
-> References
-> Classification Policy
-> Initial Positioning
-> Spiral Learning
-> Method Routing
-> Claim Verification
-> Derivation Trust
-> Test Mode
-> Weekly Review

## Data layers

Main YAML records are current-state snapshots only. Keep them short, readable, and manually editable.

Historical state changes go into append-only JSONL event logs under `data/events/YYYY-MM.jsonl`.

Sessions store the raw or semi-raw learning footprint: what happened, what AI was used for, what remained unresolved, which references were used, and what should happen next.

Do not append long histories into YAML records.

Time is a core dimension of learning state. Temporal traces distinguish short-term confusion, long-term forgetting, repeated misconception, and review due.

## Learning object routing

Use the right learning-state object:

- "What is X?" -> PositionDecision.
- "What is the difference between X and Y?" -> DistinctionRecord.
- "I thought X was Y" -> MisconceptionRecord.
- "X, Y, Z always appear together" -> ConceptClusterRecord.
- "I think X is related to Y" -> ClaimRecord.
- "I need to trust this formula/result" -> DerivationRecord.
- "I think I have learned this" -> TestRecord.

Adjacent concepts should use DistinctionRecord. This is not a knowledge-graph edge; it records a learner-specific confusion or boundary problem.

Repeated wrong ideas should use MisconceptionRecord and recurrence counts, plus event logs.

## Knowledge layers

Position decisions classify knowledge relative to a learning goal:

- A_no_ai_internalization: must enter the learner's head as disciplinary language.
- B_knowledge_positioning: must know position, use, and relation; details can be restored by AI.
- C_index_recall: only needs to be remembered as an entry point.

These are learning strategy judgments, not absolute truths. A/B/C is a dynamic classification grammar, not a fixed map of a whole field. Deep Research should help produce classification policies and heuristics, not static domain classifications.

## Visual explanation protocol

AI should actively consider visual explanation when concepts are geometric, dynamic, relational, experimental, diagrammatic, or repeatedly confused.

The system stores visual metadata and usage purpose, not large media files by default.

Priority order:
- literature figures from the paper/textbook/lecture note currently being studied;
- reliable external visuals from authoritative sources;
- AI-generated schematics, clearly labeled as illustrative teaching aids and not evidence;
- system-generated diagrams for learning-state timelines and workflows.

Do not download copyrighted materials automatically.

## Epistemic discipline

Every important claim or AI-assisted conclusion should distinguish:

- strict_fact
- derived_result
- standard_interpretation
- heuristic
- analogy
- inference
- speculation
- learning_strategy
- wrong
- open_question

Do not mix analogy with theorem, or learning strategy with disciplinary fact.

## Derivation trust

For core concepts and core tools, the system should record whether the learner personally derived or reconstructed key steps.

A derivation record should distinguish:
- user-derived steps;
- AI-hinted steps;
- not-yet-trusted steps.

## Engineering rules

- Keep the MVP CLI-first.
- Use Markdown/YAML local storage.
- Prefer transparent files over hidden databases.
- The references folder stores durable source entries, not AI summaries.
- Visual records store source metadata, reliability, purpose, and copyright notes, not an image database.
- Main records store current state only; histories go into JSONL events.
- Sessions store raw learning footprint.
- Method routing should reduce learning friction, not add bureaucracy.
- Test mode can be user-triggered or system-suggested.
- The Web UI should display a learning cockpit, not an encyclopedia.
- The default Dashboard should show only Active Goal, Primary Next Action, Open Loops, Trust Gaps, Ready for Test, and Recent Activity.
- Hide provider controls, context packs, indexes, raw events, raw YAML, debug validation, and other metadata behind Advanced surfaces.
- Use compact, calm, academic UI; avoid marketing hero layouts, decorative visuals, noisy tables, and database-admin presentation.
- API mode is the default UI interaction when a provider is configured, but every provider run must be an explicit user action with compact context preview.
- Prompt mode must remain a complete fallback when no provider is configured.
- Use the lightweight English/中文 translation dictionary for interface text; do not translate learner-authored records.
- Prompts are first-class actions in the UI.
- Codex works as an external agent by editing local files.
- Keep the frontend local-only; do not add hosted services or remote state.
- Optional provider-backed AI runs must be user-configured, explicit, previewed, and artifact-only.
- Never commit API keys or private learner data.
- Do not add AI API calls for visual generation or visual search.
- Generate copyable prompts as fallback; connected mode sends only selected context.
- Add tests for all core logic.
- Tests must pass before claiming implementation complete.
- Keep code simple, typed, and extensible.
- Default to light records; heavy records only for core concepts/tools.

## Non-goals

Do not:
- build a static knowledge graph;
- scrape or store large world knowledge;
- save large AI-generated encyclopedic notes by default;
- store Deep Research output as final truth;
- automate Socratic questioning by default;
- decide that something is "learned" without evidence.
- send learner data to a provider without explicit user action.

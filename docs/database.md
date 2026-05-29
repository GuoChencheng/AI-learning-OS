# Database

SQLite is used for local tests and development. Production deployments should use Postgres with pgvector.

`docker-compose.yml` starts:

- `postgres` using `pgvector/pgvector:pg16`;
- `redis` for future background work.

The Postgres schema is in [database.sql](database.sql). It includes:

- `users`
- `projects`
- `project_settings`
- `system_settings`
- `references`
- `reference_chunks`
- `goal_stacks`
- `messages`
- `context_packs`
- `learning_units`
- `learning_unit_turns`
- `claims`
- `distinctions`
- `temporal_traces`
- `knowledge_positions`
- `epistemic_marks`
- `derivation_trust_records`
- `review_triggers`
- `misconception_records`
- `module_runs`
- `state_update_logs`
- v0.4 research tables: `research_questions`, `hypotheses`, `evidence_records`, `competing_explanations`, `advisor_feedback`, `next_experiments`

The lightweight runtime schema lives in `src/ailearn/db/database.py` and mirrors the same table set, with JSON stored as text and embeddings stubbed unless a provider is configured.

## Persistence Policy

Durable tables store learner-side evidence and state, not every AI intermediate judgment. `messages`, `claims`, `distinctions`, `temporal_traces`, `knowledge_positions`, `derivation_trust_records`, `review_triggers`, `references`, and `state_update_logs` are the primary learning memory.

Assessment fields extend the learning memory without turning it into a world-knowledge graph:

- `knowledge_positions.last_assessed_at`, `last_assessment_result`, and `assessment_evidence` store no-AI A0-A4 evidence.
- `distinctions.status`, `confusion_count`, `last_test_result`, and `next_distinction_test_at` support test/retest loops.
- `derivation_trust_records.trust_status` and `last_step_assessment` summarize step-level derivation trust.
- `review_triggers.status` now includes `failed`; `completed_at`, `result_evidence`, `failure_reason`, and `next_retry_time` preserve outcome evidence.
- `misconception_records` stores recurring learner-side wrong patterns with stable keys, recurrence counts, severity, and next action.

`context_packs` remains in the schema for debug/audit inspection, but chat turns do not persist context packs by default. Enable `AI_LEARN_DEBUG_PERSIST_CONTEXT=1` only when an audit trail of runtime context selection is needed.

`learning_units` and `learning_unit_turns` store short-lived working context for a continuous teaching method. They let the orchestrator reuse a unit context snapshot across turns. They are not the learner's final memory; durable learning state still lives in claims, distinctions, traces, positions, derivation trust records, review triggers, references, and update logs.

Reference chunks are stored in `reference_chunks` and can be selected into a runtime ContextPack by deterministic ranking. The selected chunk excerpts are copied into `learning_units.context_snapshot_json` only as working context for the active unit.

Learning-unit close distillation writes through the same state-update path as normal StateWriter output. The resulting `state_update_logs.payload_json` includes `source_type=system_trace`, the unit close evidence string, and the durable records created from learner-side evidence.

`state_update_logs.payload_json` preserves source metadata for each state write, including source message id, source type, evidence text, durable records created, AI-only observations, and ephemeral judgments that were deliberately discarded.

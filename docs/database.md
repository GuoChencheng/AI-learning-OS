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
- `module_runs`
- `state_update_logs`
- v0.4 research tables: `research_questions`, `hypotheses`, `evidence_records`, `competing_explanations`, `advisor_feedback`, `next_experiments`

The lightweight runtime schema lives in `src/ailearn/db/database.py` and mirrors the same table set, with JSON stored as text and embeddings stubbed unless a provider is configured.

## Persistence Policy

Durable tables store learner-side evidence and state, not every AI intermediate judgment. `messages`, `claims`, `distinctions`, `temporal_traces`, `knowledge_positions`, `derivation_trust_records`, `review_triggers`, `references`, and `state_update_logs` are the primary learning memory.

`context_packs` remains in the schema for debug/audit inspection, but chat turns do not persist context packs by default. Enable `AI_LEARN_DEBUG_PERSIST_CONTEXT=1` only when an audit trail of runtime context selection is needed.

`learning_units` and `learning_unit_turns` store short-lived working context for a continuous teaching method. They let the orchestrator reuse a unit context snapshot across turns. They are not the learner's final memory; durable learning state still lives in claims, distinctions, traces, positions, derivation trust records, review triggers, references, and update logs.

`state_update_logs.payload_json` preserves source metadata for each state write, including source message id, source type, evidence text, durable records created, AI-only observations, and ephemeral judgments that were deliberately discarded.

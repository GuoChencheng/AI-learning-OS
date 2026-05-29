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

# AGENTS.md

## Product Identity

AI Learn OS is now a Web-first, API-first ChatGPT-style learning operating system.

The main product is not the old CLI-first YAML workflow. The old CLI can remain as a compatibility/helper surface, but new work should target the Web/API product.

## Product Rules

- The first screen must be a minimal conversation interface.
- Complexity belongs in the backend and the hidden right drawer, not in the main chat flow.
- Every `/api/chat` request must pass through the Orchestrator pipeline.
- Every `/api/run-next` request must choose a next action from learning state, not random text generation.
- AI automatic teaching-method selection is the default interaction.
- Manual teaching-method controls are collapsed by default and are one-turn/unit-switch overrides.
- Context preprocessing is learning-unit scoped: run full extraction at unit start or refresh, then reuse unit context across follow-up turns.
- Reference context should include ranked reference chunks when relevant, not just reference titles.
- Agent outputs must be structured Pydantic models.
- State writes must be traceable in `state_update_logs` and reversible where practical.
- AI judgments are computation, not memory: context extraction, state judgment, and routing are ephemeral unless explicitly debug-persisted.
- Durable memory should store learner-originated evidence and state, not every AI intermediate judgment or generic explanation.
- Context packs are runtime objects by default. Persist them only for debug/audit with `AI_LEARN_DEBUG_PERSIST_CONTEXT=1`.
- Learning units store short-lived working context and unit turns. They are not permanent knowledge records.
- State Writer must distill post-turn learner state and separate `user_originated_updates`, `ai_only_observations`, and `discarded_ephemeral_judgments`.
- Learning-unit closure must run learner-state distillation when the unit ends, switches method, goes stale, or Run Next jumps to a higher-priority blocker.
- Tests must use `FakeModelGateway`; do not require real API keys.
- Model routing must support `fast`, `medium`, and `strong` tiers for OpenAI-compatible providers. Final answers use `strong`; structured state writing and unit-close distillation use `medium`; all model-backed behavior must keep deterministic fallback.
- Do not commit API keys, `.env`, `config.yaml`, real learner data, caches, build outputs, or local databases.

## Learning-State Objects

Store learning state, not world knowledge:

- Claim
- Distinction
- Temporal Trace
- Knowledge Position
- Epistemic Mark
- Derivation Trust
- Review Trigger
- Module Run
- State Update Log

Adjacent concepts should become `Distinction` records. Repeated wrong ideas should be tracked as review/misconception pressure rather than encyclopedia content.

## UI Rules

- Main UI: conversation flow, bottom input, send, run-next, collapsed method override, project selector.
- Right drawer tabs: Projects, Project Settings, System Settings, Learning State.
- Keep the UI compact, calm, academic, and local-first.
- Do not expose raw database/admin surfaces in the main screen.
- Provider calls must remain explicit user actions.

## Engineering Rules

- Add tests for core logic.
- Run `python -m compileall src`, `python -m pytest -q`, `cd web && npm run typecheck`, and `cd web && npm run build` before claiming completion.
- Prefer small typed modules with clear boundaries.
- Use SQLite for tests/local fallback and keep Postgres + pgvector as the production database path.
- Keep docs aligned with the Web-first product. Old "no frontend/no API/no database" constraints are deprecated.

# AGENTS.md

## Product Identity

AI Learn OS is now a Web-first, API-first ChatGPT-style learning operating system.

The main product is not the old CLI-first YAML workflow. The old CLI can remain as a compatibility/helper surface, but new work should target the Web/API product.

## Product Rules

- The first screen must be a minimal conversation interface.
- Complexity belongs in the backend and the hidden right drawer, not in the main chat flow.
- Every `/api/chat` request must pass through the Orchestrator pipeline.
- Every `/api/run-next` request must choose a next action from learning state, not random text generation.
- Agent outputs must be structured Pydantic models.
- State writes must be traceable in `state_update_logs` and reversible where practical.
- Tests must use `FakeModelGateway`; do not require real API keys.
- Model routing must support `fast`, `medium`, and `strong` tiers for OpenAI-compatible providers.
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

- Main UI: conversation flow, bottom input, send, run-next, left teaching actions, project selector.
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

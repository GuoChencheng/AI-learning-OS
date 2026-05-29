# Architecture

AI Learn OS uses seven layers.

1. Frontend UI: React/Vite ChatGPT-style shell with teaching actions, run-next, project switcher, and hidden state/settings drawer.
2. API Gateway: `/api/*` JSON endpoints. The local runtime currently exposes a lightweight app object and is dependency-ready for FastAPI deployment.
3. Orchestrator: `ChatOrchestrator` and `RunNextOrchestrator` enforce the full pipeline and emit traces.
4. Agent Layer: eight deterministic v0.1 agents with Pydantic JSON contracts.
5. Data Layer: SQLite local runtime plus Postgres/pgvector schema for production.
6. Model Gateway: fast / medium / strong tiers, `FakeModelGateway` for tests, OpenAI-compatible gateway for configured providers.
7. State Update Layer: `StateWriterService` writes claims, distinctions, traces, review triggers, and reversible update logs.

The legacy CLI remains available for old YAML workflows, but new product behavior should be implemented through these layers.

# Architecture

AI Learn OS uses seven layers.

1. Frontend UI: React/Vite ChatGPT-style shell with teaching actions, run-next, project switcher, and hidden state/settings drawer.
2. API Gateway: `/api/*` JSON endpoints. The local runtime currently exposes a lightweight app object and is dependency-ready for FastAPI deployment.
3. Orchestrator: `ChatOrchestrator` and `RunNextOrchestrator` enforce the full pipeline and emit traces.
4. Agent Layer: eight deterministic v0.1 agents with Pydantic JSON contracts.
5. Data Layer: SQLite local runtime plus Postgres/pgvector schema for production.
6. Model Gateway: fast / medium / strong tiers, `FakeModelGateway` for tests, OpenAI-compatible gateway for configured providers.
7. State Update Layer: `StateWriterService` writes claims, distinctions, traces, review triggers, and reversible update logs.

## Ephemeral Computation vs Durable Memory

AI judgments are computation, not memory. Context extraction, state judgment, and module routing are ephemeral by default: they may appear in `pipeline_trace`, but they must not be promoted into durable learner memory unless grounded in user-originated evidence.

The durable database stores learner-side state: raw user messages, user-originated claims, learner confusions and distinctions, temporal traces, knowledge positions, derivation trust records, review triggers, selected references, and reversible state update logs.

`ContextPack` is still built on every chat turn as a runtime object, but `context_packs` persistence is disabled by default. Set `AI_LEARN_DEBUG_PERSIST_CONTEXT=1` only when debug/audit persistence is needed.

The post-turn State Writer acts as a learner-state distiller. It separates `user_originated_updates`, `ai_only_observations`, and `discarded_ephemeral_judgments`; only user-originated updates are applied to durable learning state by default.

The legacy CLI remains available for old YAML workflows, but new product behavior should be implemented through these layers.

# Architecture

AI Learn OS uses seven product layers plus an assessment service layer.

1. Frontend UI: React/Vite ChatGPT-style shell with auto method selection, collapsed manual teaching tools, run-next, project switcher, and hidden state/settings drawer.
2. API Gateway: `/api/*` JSON endpoints. The local runtime currently exposes a lightweight app object and is dependency-ready for FastAPI deployment.
3. Orchestrator: `ChatOrchestrator` and `RunNextOrchestrator` enforce the full pipeline and emit traces.
4. Agent Layer: eight deterministic v0.1 agents with Pydantic JSON contracts plus model-backed wrappers where configured.
5. Data Layer: SQLite local runtime plus Postgres/pgvector schema for production.
6. Model Gateway: fast / medium / strong tiers, `FakeModelGateway` for tests, OpenAI-compatible gateway for configured providers.
7. State Update Layer: `StateWriterService` writes claims, distinctions, traces, review triggers, unit-close distillation output, and reversible update logs.
8. Assessment Layer: deterministic/model-optional evaluators score no-AI reconstruction, derivation trust, distinction tests, claim epistemic status, misconception recurrence, and review-trigger outcomes.

## Model Tiers

The deterministic pipeline remains the fallback and all tests run without real API keys. When a real OpenAI-compatible provider is configured, model-backed wrappers use tiers by responsibility:

- Fast: future lightweight intent, context, and status judgments.
- Medium: structured learner-state writing and learning-unit close distillation.
- Strong: final teaching answer generation.

`AnswerComposer` uses the strong tier because it produces the learner-facing teaching response. `StateWriter` and the unit close distiller use the medium tier because they produce schema-validated state proposals that are sanitized before persistence. Invalid model output, gateway failure, or missing provider configuration falls back to deterministic agents.

## Ephemeral Computation vs Durable Memory

AI judgments are computation, not memory. Context extraction, state judgment, and module routing are ephemeral by default: they may appear in `pipeline_trace`, but they must not be promoted into durable learner memory unless grounded in user-originated evidence.

The durable database stores learner-side state: raw user messages, user-originated claims, learner confusions and distinctions, temporal traces, knowledge positions, derivation trust records, review triggers, selected references, and reversible state update logs.

`ContextPack` is still a runtime object, but `context_packs` persistence is disabled by default. Set `AI_LEARN_DEBUG_PERSIST_CONTEXT=1` only when debug/audit persistence is needed.

The post-turn State Writer acts as a learner-state distiller. It separates `user_originated_updates`, `ai_only_observations`, and `discarded_ephemeral_judgments`; only user-originated updates are applied to durable learning state by default.

## Learning Assessment Loop

AI Learn OS does not merely record that learning happened. It evaluates whether the learner demonstrated evidence:

- No-AI reconstruction is scored A0-A4, with A4 reserved for delayed review success.
- Derivation trust updates `done_by_user`, `hinted_by_ai`, and `untrusted_steps` separately.
- Distinctions move through `needs_test`, `partially_clear`, `clear`, `failed`, and `needs_retest`.
- Claims are marked as fact, inference, analogy, learning strategy, wrong, or open question according to user-side evidence.
- Recurring misconceptions are tracked as durable learner blockers.
- Review triggers can be completed, failed, or skipped, and Run Next ignores completed/skipped triggers.

These assessments are still computation until grounded in user evidence. Durable changes are written through repository methods and `state_update_logs`, preserving source evidence and allowing later reversal.

## Learning Unit Context

Context preprocessing is unit-scoped, not turn-scoped. A learning unit is a short-lived working session for one method, such as Socratic questioning, derivation coaching, exercise correction, review, comparison, or no-AI reconstruction.

At unit start or explicit refresh, the orchestrator runs full context extraction and stores a compact `context_snapshot_json` on the learning unit. Subsequent turns reuse that snapshot plus recent `learning_unit_turns`, so they do not scan all project state again unless the unit closes, switches method, drifts topic, or refreshes.

Learning unit context is working memory, not final learner memory. Durable learner memory is still written by post-turn or unit-close distillation into claims, distinctions, temporal traces, knowledge positions, derivation trust records, review triggers, and update logs.

When a unit closes because the learner asks to end it, a manual method switch occurs, max turns are reached, topic drift is detected, or Run Next jumps to a global priority, the close distiller summarizes the unit and writes only learner-side durable evidence. Low-content units usually produce a temporal trace only.

## Reference Context

References are still durable user-selected sources, but context extraction now includes ranked reference chunks, not just reference titles. The ranking is deterministic in the alpha build: request keywords are matched against chunk text and reference metadata, then the top chunks are formatted into `ContextPack.reference_context`.

Reference chunks enter the runtime ContextPack at learning-unit start or refresh. Reused learning-unit turns keep using the snapshot so references are not re-ranked on every turn.

Manual teaching tools are hidden by default. The learner can expand them to override the automatic method for one turn; conflicting manual overrides close the current unit and start a new one.

The legacy CLI remains available for old YAML workflows, but new product behavior should be implemented through these layers.

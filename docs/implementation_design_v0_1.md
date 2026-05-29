# AI Learn OS Implementation Design v0.1

The v0.1 product is a ChatGPT-style learning operating system.

Users interact through a single conversation surface. Each `/api/chat` request runs through eight structured agents: Request Intake, Project Resolver, Context Extractor, Context Pack Builder, State Judge, Module Router, Answer Composer, and State Writer.

By default, the learner just asks normally and AI Learn OS selects the teaching method automatically. Manual teaching tools are a collapsed override surface; selecting one starts or switches the current short-lived learning unit for that method.

The alpha implementation keeps deterministic fallback while allowing real AI assistance. Final teaching answers use the strong model tier through the Model Gateway when configured. Structured state writing and learning-unit close distillation use the medium tier, validate Pydantic output, sanitize over-recording, and fall back to deterministic agents whenever model output is unavailable or invalid.

## Learning Unit Context

Context preprocessing happens at the learning-unit boundary. A learning unit stores a compact context snapshot for one continuous micro-session, such as Socratic questioning, derivation coaching, exercise correction, review, comparison, or no-AI reconstruction. Follow-up turns reuse the snapshot and recent unit turn summaries instead of re-running full project-state context extraction every time.

Learning unit context is working memory. It can guide the current sequence, but durable learner memory is still produced only by post-turn or unit-close state distillation.

Reference preprocessing is also unit-scoped. Context extraction ranks user-added reference chunks deterministically and places the most relevant excerpts into `ContextPack.reference_context`. The selected chunks are copied into the learning-unit snapshot so follow-up turns reuse them without re-ranking the entire project.

Every turn produces:

- answer text;
- suggested next action;
- pipeline trace;
- state updates for temporal traces plus only the learner-side claims, distinctions, knowledge positions, derivation trust records, and review triggers justified by the turn.

The `/api/run-next` endpoint reads the current learning state and chooses one highest-value action in priority order: due review trigger, repeated misconception, unverified no-AI internalization, current goal next action, unresolved recent question, then new knowledge progress.

If a learning unit is active, `/api/run-next` first decides whether to continue it, refresh its context, close it, jump to a higher-priority global blocker, or create a new unit. Closing a unit runs distillation before durable state is updated.

## Learning Assessment Loop

Alpha adds assessment on top of state writing. The system now evaluates whether the learner has demonstrated understanding, distinction, derivation trust, or no-AI reconstruction:

- No-AI Test updates A0-A4 from user answers; A4 requires delayed review evidence.
- Derivation Trust separates user-derived steps, AI-hinted steps, and untrusted steps.
- Distinction records support test, failed, partially clear, clear, and retest states.
- Claim status is calibrated as strict fact, inference, analogy, learning strategy, wrong, or open question.
- Recurring misconceptions are tracked as durable learner blockers.
- Review Triggers can be completed, failed, or skipped; failed and pending due items drive Run Next priority.

Assessment writes are grounded in user-side evidence and logged in `state_update_logs`. AI-only judgments remain computation, not durable memory.

The UI keeps complexity out of the main screen. The right drawer exposes projects, project settings, system settings, and learning state.

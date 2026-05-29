# Agent Contracts

All agent outputs are Pydantic models in `src/ailearn/agents/contracts.py`.

## Request Intake Agent

```json
{"intent":"ask_concept","topic":"...","urgency":"low","needs_reference":true,"needs_state_read":true,"user_selected_mode":"auto"}
```

## Project Resolver Agent

```json
{"project_id":"proj_x","confidence":0.91,"reason":"..."}
```

## Context Extractor Agent

```json
{"relevant_goals":[],"relevant_references":[],"relevant_reference_chunks":[],"relevant_claims":[],"relevant_distinctions":[],"recent_traces":[],"active_review_triggers":[]}
```

Context extraction is an ephemeral pre-answer selector. It ranks existing durable records against the current request, but its selection is not durable learner memory.

`relevant_reference_chunks` contains deterministic top chunks selected from user-added references. Each item may include `reference_id`, `title`, `reliability_level`, `scope`, `section_title`, `page_number`, and `chunk_text`. These chunks feed the runtime ContextPack and learning-unit snapshot; they are not a new permanent knowledge graph.

## Context Pack Builder Agent

```json
{"current_request":"...","goal_context":"...","reference_context":"...","learning_state_context":"...","known_confusions":[],"must_respect_constraints":[],"suggested_learning_action":"explain","ai_permission_boundary":"direct_answer"}
```

Context packs are runtime objects. Persist them only in debug/audit mode with `AI_LEARN_DEBUG_PERSIST_CONTEXT=1`.

When an active learning unit is reused, `ContextPackBuilderAgent.run_from_learning_unit(...)` builds the runtime pack from `learning_units.context_snapshot_json`, the unit summary, recent `learning_unit_turns`, and the current request. It does not re-read all project state unless the unit is refreshed or replaced.

## State Judge Agent

```json
{"learning_state":"progressing","knowledge_layer":"positioning","record_intensity":"light","risk_flags":[]}
```

State Judge labels are computation. They can guide routing and writing, but they are not stored as learner memory by themselves.

## Module Router Agent

```json
{"module":"concept_explainer","secondary_module":"misconception_detector","reason":"...","interaction_mode":"direct_response"}
```

Routing priority is manual button, explicit selected mode, active learning unit method, project default, State Judge recommendation, then default explanation. The active unit method keeps multi-turn sequences coherent while auto method selection remains the default.

## Answer Composer Agent

```json
{"answer":"...","exercise":null,"follow_up_question":null,"suggested_next_action":"..."}
```

When a real provider is configured, `ModelBackedAnswerComposerAgent` calls the strong model tier for final teaching answers. The prompt includes the selected module, ContextPack, StateJudge output, active learning-unit metadata, settings, and reference chunks. Invalid output or gateway failure falls back to the deterministic composer.

## State Writer Agent

```json
{"new_claims":[],"updated_claims":[],"new_distinctions":[],"new_temporal_trace":{},"knowledge_position_updates":[],"derivation_trust_updates":[],"review_triggers":[],"next_recommended_action":"...","source_metadata":{"source_type":"user_question","source_message_id":"msg_x","evidence_text":"..."},"user_originated_updates":{},"ai_only_observations":{},"discarded_ephemeral_judgments":{}}
```

State Writer is a post-turn learner-state distiller. It always records a temporal trace for normal chat, then writes claims, distinctions, review triggers, knowledge positions, or derivation trust records only when the user message or chosen teaching action provides learner-side evidence.

`ModelBackedStateWriterAgent` can call the medium tier for structured state proposals. The output is validated against `StateWriterOutput` and sanitized before persistence so greetings, operational messages, ordinary explanations, and AI-only hypotheses do not become durable memory.

## Learning Unit Close Distiller

Learning-unit close distillation reuses `StateWriterOutput` as its durable-write contract. It gathers the unit, context snapshot, recent turns, method, topic, and close reason; then it writes a summary plus learner-side updates when evidence exists. Medium-tier model output is optional and deterministic fallback remains authoritative for tests.

## Assessment Contracts

Assessment outputs are Pydantic models and remain grounded in learner evidence:

- `NoAIReconstructionAssessmentOutput`: `concept`, `previous_level`, `new_level`, `result`, `evidence_text`, `reason`, `next_action`, `should_schedule_review`.
- `DerivationStepAssessmentOutput`: separates `done_by_user`, `hinted_by_ai`, `untrusted_steps`, reconstruction status, and rederive scheduling.
- `DistinctionAssessmentOutput`: marks `needs_test`, `partially_clear`, `clear`, `failed`, or `needs_retest`, with confusion-count delta and next test prompt.
- `ClaimEpistemicAssessmentOutput`: refines `epistemic_status`, durable claim `status`, confidence, caveat/correction, and evidence.
- `MisconceptionRecurrenceOutput`: records stable misconception key, related records, recurrence delta, severity, evidence, and next action.

The assessment layer may use the medium tier in configured mode, but deterministic fallback is the test path. Assessment judgments are not durable memory until repository update methods apply them with source evidence.

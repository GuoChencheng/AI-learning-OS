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
{"relevant_goals":[],"relevant_references":[],"relevant_claims":[],"relevant_distinctions":[],"recent_traces":[],"active_review_triggers":[]}
```

Context extraction is an ephemeral pre-answer selector. It ranks existing durable records against the current request, but its selection is not durable learner memory.

## Context Pack Builder Agent

```json
{"current_request":"...","goal_context":"...","reference_context":"...","learning_state_context":"...","known_confusions":[],"must_respect_constraints":[],"suggested_learning_action":"explain","ai_permission_boundary":"direct_answer"}
```

Context packs are runtime objects. Persist them only in debug/audit mode with `AI_LEARN_DEBUG_PERSIST_CONTEXT=1`.

## State Judge Agent

```json
{"learning_state":"progressing","knowledge_layer":"positioning","record_intensity":"light","risk_flags":[]}
```

State Judge labels are computation. They can guide routing and writing, but they are not stored as learner memory by themselves.

## Module Router Agent

```json
{"module":"concept_explainer","secondary_module":"misconception_detector","reason":"...","interaction_mode":"direct_response"}
```

## Answer Composer Agent

```json
{"answer":"...","exercise":null,"follow_up_question":null,"suggested_next_action":"..."}
```

## State Writer Agent

```json
{"new_claims":[],"updated_claims":[],"new_distinctions":[],"new_temporal_trace":{},"knowledge_position_updates":[],"derivation_trust_updates":[],"review_triggers":[],"next_recommended_action":"...","source_metadata":{"source_type":"user_question","source_message_id":"msg_x","evidence_text":"..."},"user_originated_updates":{},"ai_only_observations":{},"discarded_ephemeral_judgments":{}}
```

State Writer is a post-turn learner-state distiller. It always records a temporal trace for normal chat, then writes claims, distinctions, review triggers, knowledge positions, or derivation trust records only when the user message or chosen teaching action provides learner-side evidence.

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

## Context Pack Builder Agent

```json
{"current_request":"...","goal_context":"...","reference_context":"...","learning_state_context":"...","known_confusions":[],"must_respect_constraints":[],"suggested_learning_action":"explain","ai_permission_boundary":"direct_answer"}
```

## State Judge Agent

```json
{"learning_state":"progressing","knowledge_layer":"positioning","record_intensity":"light","risk_flags":[]}
```

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
{"new_claims":[],"updated_claims":[],"new_distinctions":[],"new_temporal_trace":{},"knowledge_position_updates":[],"derivation_trust_updates":[],"review_triggers":[],"next_recommended_action":"..."}
```

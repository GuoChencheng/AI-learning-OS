# API

All responses are JSON.

## Chat

`POST /api/chat`

```json
{"project_id":"proj_x","message":"二阶相变处一定是 CFT 吗？","selected_mode":"auto","button_action":null}
```

Returns `answer`, `suggested_next_action`, `pipeline_trace`, `state_updates`, and optionally `active_learning_unit`.

`pipeline_trace` may include ephemeral context extraction, state judgment, routing outputs, and learning-unit metadata. These are diagnostic computation results, not durable learner memory. Context packs are not persisted unless `AI_LEARN_DEBUG_PERSIST_CONTEXT=1`.

Full context extraction runs when a learning unit starts or refreshes. If the active unit is reused, the trace marks `learning_unit.should_run_full_context_extraction=false`.

When references are relevant, the runtime context pack contains ranked reference chunk excerpts in `reference_context`. If debug context persistence is enabled, those excerpts are visible in the persisted `context_packs` row; otherwise they remain in the trace and learning-unit snapshot only.

## Run Next

`POST /api/run-next`

```json
{"project_id":"proj_x"}
```

Returns the chosen module, reason, answer, pipeline trace, and state updates.

Additional backend explainability fields are included for future UI use:

```json
{"priority":"due_review_trigger","loop_step":"review","why_this_now":"...","expected_user_action":"...","will_update":["temporal_trace"]}
```

`/api/run-next` also returns `active_learning_unit` when it creates or continues a learning unit.

With an active learning unit, Run Next may:

- `continue_active_unit` when the unit is still valid;
- `refresh_active_unit` when the unit snapshot requests refresh;
- `close_active_unit` when the unit is stale or over turn limit;
- `jump_to_global_priority` when a due review trigger, repeated misconception, or no-AI gap outranks the active unit;
- `create_new_unit` when no active unit exists.

## Learning Units

- `GET /api/projects/:id/learning-units/active`
- `GET /api/projects/:id/learning-units`
- `POST /api/projects/:id/learning-units/:unit_id/close`
- `POST /api/projects/:id/learning-units/:unit_id/refresh-context`

Learning units hold short-lived method context. They are not permanent knowledge records. Closing a unit marks it closed, preserves its summary, and runs close-time state distillation. Refreshing marks or updates the context snapshot for the next run.

## Projects

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/:id`
- `PATCH /api/projects/:id`

## Settings

- `GET /api/projects/:id/settings`
- `PATCH /api/projects/:id/settings`
- `GET /api/system-settings`
- `PATCH /api/system-settings`
- `GET /api/settings/providers`
- `PATCH /api/settings/providers`

`PATCH /api/settings/providers` stores OpenAI-compatible provider settings in local ignored storage, normally `.env.local`. The request may include `api_key`, `base_url`, `fast_model`, `medium_model`, and `strong_model`. The response reports whether a key is present, but never returns the key value.

## Learning State

- `GET /api/projects/:id/state`
- `GET /api/projects/:id/learning-summary`
- `GET /api/projects/:id/claims`
- `GET /api/projects/:id/distinctions`
- `GET /api/projects/:id/review-triggers`
- `GET /api/projects/:id/knowledge-positions`

`GET /api/projects/:id/learning-summary` returns a compact Inspector payload:

```json
{
  "current_blocker": {"type": "misconception", "title": "...", "reason": "...", "evidence": "...", "related_ids": []},
  "primary_next_action": {"module": "flawed_interpretation_critic", "label": "...", "reason": "...", "expected_user_action": "..."},
  "evidence": [],
  "counts": {"open_claims": 0, "failed_reviews": 0, "recurring_misconceptions": 0, "no_ai_below_A3": 0, "derivation_trust_gaps": 0, "distinctions_needing_test": 0}
}
```

Priority order is due pending/failed review, recurring misconception, no-AI gap below A3, derivation trust gap, distinction needing test, then open/wrong claim.

Review trigger outcome endpoints:

- `POST /api/review-triggers/:id/complete`
- `POST /api/review-triggers/:id/fail`
- `POST /api/review-triggers/:id/skip`

Payloads can include `evidence_text`, `result_note`, `failure_reason`, and `next_retry_time`. Completion, failure, and skip are logged as assessment updates; failed reviews can schedule a retry.

## References

- `POST /api/projects/:id/references`
- `POST /api/projects/:id/references/upload`
- `GET /api/projects/:id/references`
- `GET /api/references/:id/chunks`

## State Update Revert

`POST /api/state-updates/:id/revert`

Marks claims from the update as deprecated and review triggers as skipped.

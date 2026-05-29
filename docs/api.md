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

## Learning Units

- `GET /api/projects/:id/learning-units/active`
- `GET /api/projects/:id/learning-units`
- `POST /api/projects/:id/learning-units/:unit_id/close`
- `POST /api/projects/:id/learning-units/:unit_id/refresh-context`

Learning units hold short-lived method context. They are not permanent knowledge records. Closing a unit marks it closed and preserves its summary; refreshing marks or updates the context snapshot for the next run.

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

## Learning State

- `GET /api/projects/:id/state`
- `GET /api/projects/:id/claims`
- `GET /api/projects/:id/distinctions`
- `GET /api/projects/:id/review-triggers`
- `GET /api/projects/:id/knowledge-positions`

## References

- `POST /api/projects/:id/references`
- `POST /api/projects/:id/references/upload`
- `GET /api/projects/:id/references`
- `GET /api/references/:id/chunks`

## State Update Revert

`POST /api/state-updates/:id/revert`

Marks claims from the update as deprecated and review triggers as skipped.

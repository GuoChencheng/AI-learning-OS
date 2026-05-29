# API

All responses are JSON.

## Chat

`POST /api/chat`

```json
{"project_id":"proj_x","message":"二阶相变处一定是 CFT 吗？","selected_mode":"auto","button_action":null}
```

Returns `answer`, `suggested_next_action`, `pipeline_trace`, and `state_updates`.

`pipeline_trace` may include ephemeral context extraction, state judgment, and routing outputs. These are diagnostic computation results, not durable learner memory. Context packs are not persisted unless `AI_LEARN_DEBUG_PERSIST_CONTEXT=1`.

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

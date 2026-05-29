# Alpha Feature Audit

This audit describes the current alpha product state after the learning-loop wiring pass. Status terms:

- `usable`: implemented, reachable through API or UI, and covered by tests or smoke flow.
- `partially usable`: implemented but limited, incomplete, or not fully reversible/exposed.
- `implemented but not exposed`: backend exists, but the normal UI does not make it first-class.
- `test-only`: verified through deterministic tests but not a normal product path.
- `missing`: not implemented.

## Core Project Flow

| Feature | Status | Evidence / Notes |
|---|---:|---|
| Create project | usable | `POST /api/projects`; Projects tab create field. |
| Switch project | usable | Top HUD selector and Projects tab call local state switch. |
| Update project settings | usable | `PATCH /api/projects/:id/settings`; Inspector fields write directly. |
| Update system settings | usable | `PATCH /api/system-settings`; Inspector fields write directly. |
| Create CFT seed project | partially usable | `POST /api/projects/seed/cft` works; UI has API client but no first-class CFT seed button yet. |
| Load project state | usable | `GET /api/projects/:id/state`; Inspector Learning State tab. |
| Load learning summary | usable | `GET /api/projects/:id/learning-summary`; Inspector summary card. |
| Paste Reference | usable | Inspector Reference form calls `POST /api/projects/:id/references`. |
| Upload Reference | usable | txt/md/pdf upload path exists; PDF requires optional `pypdf`. |
| Retrieve Reference chunks | usable | `GET /api/references/:id/chunks`; tests verify chunk creation. |
| Send chat message | usable | Smart Input calls `/api/chat`; full 8-agent pipeline is returned. |
| Run Next | usable | Empty-input button calls `/api/run-next`; returns priority, loop step, decision fields, active unit. |
| Learning Unit creation | usable | Chat/manual modes and Run Next can create units. |
| Learning Unit reuse | usable | Follow-up chat reuses active unit and skips full context extraction. |
| Learning Unit refresh | usable | Refresh endpoint marks `refresh_requested`; next chat/run-next refreshes context. |
| Learning Unit close | usable | Chat close phrase, Run Next stale/max-turn close, manual method switch, and close endpoint now run close-time distillation. |
| StateWriter selective write | usable | Temporal trace always written; claims/distinctions/reviews are gated by learner evidence. |
| Unit close distillation | usable | Uses Medium model tier with deterministic fallback; logs `unit_close` source metadata. |
| State update revert | partially usable | Reverts selected created records such as claims/review triggers/positions/derivations; not a complete transaction rollback for every table. |

## AI Path Validation

| Path | Status | Notes |
|---|---:|---|
| FakeModelGateway path | usable | Default when `OPENAI_API_KEY` is absent; tests use it. |
| OpenAICompatibleGateway path | usable | `create_model_gateway_from_env()` selects it when `OPENAI_API_KEY` is set. |
| Environment gateway factory | usable | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and tier model env vars are read. |
| Strong AnswerComposer | usable | `ModelBackedAnswerComposerAgent` calls `ModelTier.STRONG`. |
| Medium StateWriter | usable | `ModelBackedStateWriterAgent` calls `ModelTier.MEDIUM` and sanitizes output. |
| Medium UnitCloseDistiller | usable | `LearningUnitCloseDistiller` calls `ModelTier.MEDIUM`. |
| Deterministic fallback | usable | Gateway failures and invalid structured output fall back without corrupting state. |
| Invalid JSON fallback | usable | `ModelGateway.complete_structured` falls back when schema validation fails. |
| Provider missing fallback | usable | No key selects Fake gateway; missing/failed real provider calls fall back at agent layer. |
| Model tier recording | partially usable | Chat response exposes `model_path`; module runs record final answer tier. Medium statewriter/distiller tier is test-verified but not fully surfaced in UI. |

Run diagnostics:

```bash
.venv/bin/python scripts/check_ai_path.py
```

It prints selected gateway, configured tier model names, base URL, and whether a key is configured. It never prints the key value.

## Learning Assessment

| Feature | Status | Evidence / Notes |
|---|---:|---|
| No-AI A0-A4 scoring | usable | `NoAITestEvaluator`; A4 requires delayed-review evidence. |
| DerivationTrust step update | usable | Updates done-by-user, hinted-by-AI, untrusted steps, trust status, and rederive schedule. |
| Distinction test/retest | usable | Marks clear/partial/failed, increments confusion count, schedules review. |
| Claim epistemic assessment | usable | Refines learner claims into wrong/analogy/inference/learning_strategy/open_question. |
| Misconception recurrence | usable | Stable keys; repeated errors become recurring and create/reuse review triggers. |
| ReviewTrigger complete/fail/skip | usable | API endpoints update status and evidence; Run Next ignores completed/skipped. |
| Learning-summary current blocker | usable | Priority order: due review, recurring misconception, no-AI gap, derivation gap, distinction gap, claim gap. |
| RunNext priority after assessment | usable | Run Next now reads recurring misconception records directly before goal advancement. |

## Frontend / Visible Actions

| Button / Action | Expected Behavior | API Called | Current Status | Gap / Risk |
|---|---|---|---:|---|
| Top HUD project selector | Switch active project | none, then refresh surfaces | usable | Project list is simple; no search. |
| Settings / Inspector button | Open/close right drawer | none | usable | Drawer is state-heavy but acceptable. |
| Projects tab create | Create project | `POST /api/projects` | usable | CFT demo seed not directly exposed here. |
| Project Settings fields | Patch project/settings | `PATCH /api/projects/:id`, `PATCH /api/projects/:id/settings` | usable | Writes on field change/blur; no explicit save state. |
| System Settings fields | Patch system settings | `PATCH /api/system-settings` | usable | Model routing config visibility is basic. |
| Learning Summary Card | Show blocker, next action, evidence | `GET /api/projects/:id/learning-summary` | usable | Action affordance is read-only. |
| Reference paste save | Add reference and chunks | `POST /api/projects/:id/references` | usable | Chunk preview is not first-class. |
| Reference file upload | Upload txt/md/pdf | `POST /api/projects/:id/references/upload` | usable | PDF failure message depends on backend error. |
| `+` method menu | Manual one-turn override | included in `/api/chat` body | usable | No-AI and correction are not currently shown in the compact popover. |
| Send | Chat through orchestrator | `POST /api/chat` | usable | Backend must be running; frontend reports empty/non-JSON responses clearly. |
| Empty-input Run Next | Choose next learning action | `POST /api/run-next` | usable | Decision chip is muted; not enough for complex review actions. |
| State update revert | Revert recent writeback | `POST /api/state-updates/:id/revert` | partially usable | Not a complete rollback for every table. |
| Metadata chips | Show model path/unit/reference count | response metadata and trace | usable | Source preview is hover-only and minimal. |
| Review complete/fail/skip | Mark review result | endpoints exist | implemented but not exposed | Needs designer pass. |
| Start No-AI test from blocker | Launch focused no-AI response | `/api/chat` with no-ai action | implemented but not exposed | No dedicated no-AI mode surface. |
| Submit derivation step tied to record | Assess derivation attempt | assessment runs through chat trigger | implemented but not exposed | No step tracker UI. |
| Submit distinction answer tied to record | Assess boundary answer | assessment runs through chat trigger | implemented but not exposed | No focused distinction test card. |
| Close active Learning Unit explicitly | Distill and close unit | `POST /api/projects/:id/learning-units/:unit_id/close` | implemented but not exposed | UI lacks explicit close button. |
| Refresh active unit context | Mark refresh and rerank context | `POST /api/projects/:id/learning-units/:unit_id/refresh-context` | implemented but not exposed | UI lacks explicit refresh. |
| CFT seed from UI | Seed demo project | `POST /api/projects/seed/cft` | implemented but not exposed | Add as a quiet demo action later. |

## Acceptance Summary

The alpha loop is now usable from API and mostly usable from the current UI:

```text
project -> reference/seed -> chat -> learning unit -> answer -> state write -> assessment -> summary -> run next
```

The largest remaining gap is not backend capability. It is focused interaction design for assessment outcomes: review pass/fail/skip, no-AI test mode, distinction retest, derivation step trust, and explicit learning-unit controls.

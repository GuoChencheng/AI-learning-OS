# UI Action Audit

This audit maps visible controls to expected behavior and backend paths. It is a wiring audit, not a redesign proposal.

## Top HUD

| Control | Location | Expected behavior | Current API call | Backend path | Status | Gap | Recommended design treatment |
|---|---|---|---|---|---:|---|---|
| Project selector | Top HUD center/left | Switch current project and reload surfaces | none, then settings/state/summary/reference/unit GETs | multiple read endpoints | usable | No search for many projects | Keep minimal; add search only when project count grows. |
| State chip | Top HUD center | Show A-level and hover detail | none | data from state | usable | Hover text is cramped for long goals | Designer should tune tooltip/expansion. |
| Settings button | Top HUD right | Open/close Inspector | none | none | usable | None | Keep as one quiet icon. |

## Smart Input

| Control | Location | Expected behavior | Current API call | Backend path | Status | Gap | Recommended design treatment |
|---|---|---|---|---|---:|---|---|
| Text input | Bottom composer | Enter sends, Shift+Enter newline | none | none | usable | Single textarea is intentionally simple | Keep. |
| Send | Bottom composer | Send `/api/chat` with selected mode/action | `POST /api/chat` | ChatOrchestrator | usable | Requires backend server | Keep error strip. |
| Run Next | Bottom composer | Empty input auto-selects next action | `POST /api/run-next` | RunNextOrchestrator | usable | Does not expose review outcome controls | Keep magic button; pair with contextual outcome controls later. |
| Run decision chip | Below/right of Run Next | Show continue/refresh/jump/close/create reason | response metadata | RunNext response | usable | Very terse for complex jumps | Keep muted; expand in Inspector. |
| `+` method menu | Composer left | Show manual pedagogical overrides | none until send | ModuleRouter via chat payload | usable | `correct` and `no_ai_test` are hidden from compact menu | Add progressive advanced methods later. |
| Method options | Popover | Set one-turn override and collapse | `POST /api/chat` later | ModuleRouter priority | usable | No per-method description | Keep labels short; use tooltip only if needed. |

## Message Stream

| Control | Location | Expected behavior | Current API call | Backend path | Status | Gap | Recommended design treatment |
|---|---|---|---|---|---:|---|---|
| Assistant answer | Main stream | Render Markdown answer | `/api/chat` or `/api/run-next` | AnswerComposer | usable | None | Keep bubbleless AI message. |
| State update hint | Under assistant answer | Show compact writeback summary | response state updates | StateWriterService | usable | Does not separate assessment updates clearly | Add small assessment hint only when useful. |
| Revert writeback | Under assistant answer | Revert latest state update log | `POST /api/state-updates/:id/revert` | Repository revert | partially usable | Not full transactional undo | Label as "revert durable writeback", not whole turn undo. |
| Metadata chips | Under assistant answer | Show model path, active unit, references used | response/trace | model-backed agents, unit manager, context extractor | usable | Reference preview is hover-only | Add source popover later. |
| Reference used preview | Metadata hover | Show excerpt preview | none | trace/client metadata | partially usable | Cannot inspect all chunks or open source | Add source drawer section. |
| Model path chip | Metadata chip | Show strong/fallback | response `model_path` | AnswerComposer | usable | Medium StateWriter path not visible | Keep debug-only for non-answer tiers. |
| Active Learning Unit chip | Metadata chip | Show method/turn/context status | response/trace | LearningUnitManager | usable | No direct close/refresh controls | Add subtle unit controls in Inspector. |

## Right Inspector

| Control | Location | Expected behavior | Current API call | Backend path | Status | Gap | Recommended design treatment |
|---|---|---|---|---|---:|---|---|
| Projects tab | Inspector | Create/select project | `POST /api/projects`; surface reload | Repository | usable | No CFT seed action | Add quiet "Create CFT demo" entry. |
| Project Settings tab | Inspector | Edit settings and project mode/status | PATCH endpoints | Repository settings | usable | No dirty/save state | Current direct save is acceptable for alpha. |
| System Settings tab | Inspector | Edit global settings | `PATCH /api/system-settings` | Repository settings | usable | API key is env-only, not UI-configured | Keep keys out of UI for alpha. |
| Learning State tab | Inspector | Show summary and grouped state | state/summary GETs | Repository summary/state | usable | Dense lower lists | Keep summary first, lists secondary. |
| Learning Summary Card | Learning State tab top | Show current blocker, next action, evidence | `GET /api/projects/:id/learning-summary` | deterministic summary | usable | CTA is read-only | Add Next Action CTA later. |
| Reference save | Learning State tab | Save pasted reference | `POST /api/projects/:id/references` | Repository references | usable | No chunk preview after save | Add small "chunks created" preview later. |
| Reference upload | Learning State tab | Upload txt/md/pdf | `POST /api/projects/:id/references/upload` | extract + chunk | usable | PDF optional dependency errors need better UI copy | Surface backend error as-is for now. |
| Learning Unit display | Learning State tab | Show units | `GET /api/projects/:id/learning-units` | Repository | partially usable | Units are in state payload but not a dedicated section | Add compact Active Unit section. |
| Review Trigger visibility | Learning State tab | Show review triggers | state GET | Repository | usable | complete/fail/skip absent | Add outcome controls later. |

## Missing Important Actions

| Missing control | Backend status | Product risk | Recommendation |
|---|---:|---|---|
| Complete/fail/skip ReviewTrigger from UI | implemented | Review loop cannot be closed naturally from UI | High-priority design pass. |
| Start No-AI test from current blocker | implemented through chat button/action | Learner may not know when AI is withholding help | Dedicated No-AI test mode. |
| Submit distinction answer tied to a Distinction | implemented through conservative chat triggers | Assessment feels indirect | Distinction Test Card. |
| Submit derivation step tied to DerivationTrust record | implemented through chat triggers | Step trust is hard to inspect | Derivation Step Tracker. |
| Close active Learning Unit explicitly | endpoint implemented | User cannot end unit except via natural language | Small Inspector action. |
| Refresh active Learning Unit context explicitly | endpoint implemented | New references may not feel connected | Small Inspector action. |
| Inspect selected Reference chunks | chunks and metadata exist | User cannot audit evidence deeply | Source popover/drawer. |
| Run CFT seed from UI | endpoint and api client exist | Demo path is not discoverable | Add "Create Demo: CFT" project action. |
| See model/fallback status clearly | message chip exists | Debug info can be missed | Keep muted chip; add advanced trace toggle. |

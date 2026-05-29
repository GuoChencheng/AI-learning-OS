# Frontend Structure Gap Report

This report is for the next design pass. It describes structure and gaps without prescribing a full visual redesign.

## Current Information Architecture

```text
Top HUD
  project selector
  learning state chip
  settings / Inspector button

Main chat
  user messages
  assistant messages
  muted metadata chips
  state writeback hints

Smart Input
  + method menu
  textarea
  morphing Send / Run Next button
  run decision chip

Right Inspector
  Projects
  Project Settings
  System Settings
  Learning State
    Learning Summary Card
    durable state groups
    Reference paste/upload
```

## Current Product Behavior

The current loop is:

```text
ask
-> Request Intake
-> Project Resolver
-> Context Extractor
-> Context Pack Builder
-> State Judge
-> Module Router
-> Answer Composer
-> State Writer
-> targeted assessment when triggered
-> Learning Summary updates current blocker
-> Run Next chooses next action
```

Learning Units make context preprocessing unit-scoped rather than turn-scoped. The UI hints at this through a muted metadata chip such as `Socratic · turn 3 · context reused`.

## High-Priority UI Gaps

1. ReviewTrigger complete/fail/skip is not first-class.
   - Backend endpoints exist.
   - Current UI only shows review triggers as list items.
   - Designer should add compact outcome controls near the current blocker or review item.

2. No-AI Test needs a distinct interaction mode.
   - Backend can score A0-A4.
   - Current UI does not clearly signal "answer without AI help".
   - Add a focused no-AI card or composer state with timer/constraint copy kept minimal.

3. DerivationTrust needs step-by-step UI.
   - Backend separates user-derived, AI-hinted, and untrusted steps.
   - Current UI only shows a list summary.
   - Add a derivation step tracker with quiet status marks.

4. Distinction test/retest needs a focused answer surface.
   - Backend can mark clear/partial/failed.
   - Current chat trigger is too implicit.
   - Add a Distinction Test Card with boundary, example, counterexample answer prompt.

5. Learning Summary needs clearer evidence and action affordance.
   - Current blocker and evidence exist.
   - The next action is read-only.
   - Add one primary CTA that triggers the recommended module without making the interface busy.

6. Learning Unit status should be visible but subtle.
   - Message chips show unit state.
   - Inspector lacks a dedicated active unit section.
   - Add Active Unit Chip + close/refresh controls in Inspector.

7. Reference chunks used by answer need source preview.
   - Metadata hover shows excerpts.
   - There is no persistent source view.
   - Add Reference Source Popover or Inspector source drawer.

8. Model/fallback path needs debug visibility, not primary UI.
   - Current chip is acceptable.
   - Medium statewriter/distiller path should remain advanced/debug to avoid clutter.

9. CFT seed / sample project entry should be discoverable.
   - API exists.
   - UI lacks entry.
   - Add a quiet "Create Demo: CFT Topological Order Learning Loop" action in Projects tab.

## Suggested Components

- `CurrentBlockerCard`: shows blocker, why it matters, and evidence count.
- `NextActionCTA`: one compact action button derived from learning summary.
- `EvidenceStrip`: 2-4 muted evidence chips with source/status.
- `ReviewOutcomeControls`: complete, fail, skip with optional evidence text.
- `NoAITestMode`: composer state that asks the learner to answer without AI hints.
- `DerivationStepTracker`: user-derived / AI-hinted / untrusted step list.
- `DistinctionTestCard`: boundary answer surface with retest status.
- `ActiveLearningUnitChip`: method, turn count, context reused/refreshed.
- `ReferenceSourcePopover`: source title, reliability, section/page, excerpt.
- `DebugTraceToggle`: hides pipeline trace/model tier detail behind advanced disclosure.

## Design Constraints

- Default UI must remain quiet.
- Manual methods are overrides, not the main interaction.
- Inspector is for learning state, not database administration.
- User should see why the system chose the next action.
- Avoid making learning feel like filling forms.
- Assessment actions should feel like a natural part of conversation, not a workflow checklist.

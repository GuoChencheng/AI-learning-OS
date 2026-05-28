# Codex Task Plan

## Phase 1: Project scaffold

- Create pyproject.toml
- Create src/ailearn package
- Add CLI entry point `learn`
- Add data folders
- Add templates
- Add tests folder

## Phase 2: Schemas

Implement Pydantic models:

- Goal
- PositionDecision
- ClaimRecord
- DerivationRecord
- SessionFootprint metadata
- ReviewDraft

## Phase 3: Storage

Implement:

- YAML save/load
- Markdown with frontmatter save/load
- ID generation
- timestamp helpers
- directory initialization

## Phase 4: CLI

Implement commands:

- init
- goal
- position
- claim
- derivation
- session
- prompt
- import
- review
- validate

## Phase 5: Prompt generators

Implement:

- dynamic positioning
- claim verification
- derivation guidance
- Socratic drill
- weekly review

## Phase 6: Review generator

Read local records and produce weekly review Markdown.

## Phase 7: Validation

Validate all records and report errors.

## Phase 8: Tests and sample workflow

Run pytest and execute sample workflow.

# AI Context Loading Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add derived indexes and task-specific context packs so AI agents load only minimal learning-state context.

**Architecture:** Add `indexes.py` for derived summaries and `context.py` for context-pack policy/building. Reuse existing YAML/Markdown/JSONL storage, prompts, validation, and Typer CLI patterns. Context packs reference selected records and compact metadata instead of reading all references, sessions, or Deep Research imports.

**Tech Stack:** Python 3.11+, Typer, Pydantic, PyYAML, JSONL, Markdown, pytest.

---

### Task 1: Tests

**Files:**
- Create: `tests/test_indexes_context.py`
- Modify: `tests/test_prompts.py`
- Modify: `tests/test_validate.py`

- [ ] Write failing tests for `refresh_indexes`, `record_manifest.jsonl`, `topic_index.yaml`, `open_loops.md`, `build_context_pack`, budget behavior, docs presence, prompt context references, and validation.
- [ ] Run the targeted tests and confirm failure from missing `ailearn.indexes` / `ailearn.context` behavior.

### Task 2: Index Generation

**Files:**
- Create: `src/ailearn/indexes.py`
- Modify: `src/ailearn/storage.py`
- Modify: `src/ailearn/cli.py`

- [ ] Generate `data/indexes/active_goal_summary.md`, `open_loops.md`, `recent_activity.md`, `reference_index.yaml`, `record_manifest.jsonl`, and `topic_index.yaml`.
- [ ] Add `learn index refresh/show/active-goal/open-loops/recent/topic`.

### Task 3: Context Packs

**Files:**
- Create: `src/ailearn/context.py`
- Modify: `src/ailearn/cli.py`
- Modify: `src/ailearn/web_api.py`

- [ ] Build task-specific Markdown context packs under `data/context_packs/`.
- [ ] Support `small`, `medium`, and `large` budgets with deterministic caps.
- [ ] Add `learn context build/show/policy`.

### Task 4: Prompt Integration

**Files:**
- Modify: `src/ailearn/cli.py`
- Modify: `src/ailearn/prompts.py` if helper text is needed.

- [ ] Add `--with-context` to verify-claim, derivation, distinguish, misconception-correction, test-topic, review weekly, and method-router prompt commands.
- [ ] Include a compact context pack reference or inline pack without unbounded raw data.

### Task 5: Docs and Validation

**Files:**
- Create: `docs/core_methodology.md`
- Create: `docs/ai_context_protocol.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `src/ailearn/validate.py`

- [ ] Document minimal context loading and task routing.
- [ ] Validate index JSON/YAML and context pack size limits.

### Task 6: Verification and Demo

**Files:**
- Derived data under `data/indexes/` and `data/context_packs/`.

- [ ] Run `learn index refresh`.
- [ ] Build verify-claim and test-topic context packs.
- [ ] Run `learn context policy`, `learn prompt verify-claim ... --with-context`, `learn validate`, and `pytest`.

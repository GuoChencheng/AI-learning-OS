---
name: ui_simplicity
description: Project-level UI design workflow for keeping ai-learning-os compact, local-first, and learning-state focused.
---

# UI Simplicity Skill

Use this skill before changing `ai-learning-os` UI surfaces.

## Read First

- `AGENTS.md`
- `docs/core_methodology.md`
- `docs/ai_context_protocol.md`
- `docs/ui_design.md`
- `docs/ui_principles.md`

## Product Lens

The UI displays learning state, not world knowledge. It should answer:

- What am I learning now?
- What should I do next?
- What is unresolved?
- What needs trust, testing, or review?

## Dashboard Rule

The default dashboard may show only:

- Active Goal;
- Primary Next Action;
- Open Loops;
- Trust Gaps;
- Ready for Test;
- Recent Activity.

Put settings, raw metadata, indexes, provider controls, context packs, raw events, and YAML-like details behind Advanced disclosures or separate Advanced pages.

## Implementation Rules

- Do not change storage models to simplify a page.
- Prefer derived view objects over merging source records.
- Keep prompt/API execution visible as an action, not as the whole dashboard.
- Default to API mode when a provider is configured, but never send context without an explicit click.
- Prompt mode remains a complete fallback with no API keys.
- Keep English/中文 UI labels in the lightweight translation dictionary; do not translate user-authored records.
- Use compact card summaries, rows, and badges.
- Hide raw metadata behind `<details>` or Advanced pages.
- Preserve CLI and local-first behavior.
- No automatic AI API calls.
- No static knowledge graph.

## Verification

Preview the changed route in the Codex in-app browser or local browser. Check:

- first viewport fit;
- one clear primary next action;
- no raw YAML or event noise;
- no advanced/provider controls visible by default;
- API/Prompt mode switch remains in the sidebar footer;
- bilingual labels fit in the layout;
- text does not overflow cards;
- mobile collapse remains readable.

Run:

```bash
cd web && npm run typecheck && npm run build
.venv/bin/python -m pytest -q
```

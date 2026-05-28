# UI Principles

`ai-learning-os` UI is a local learning cockpit, not a database admin panel.

## Design Workflow

1. Read `AGENTS.md`, `docs/core_methodology.md`, `docs/ai_context_protocol.md`, `docs/ui_design.md`, and this file.
2. Identify whether the change affects daily learning flow or advanced/debug flow.
3. Keep the default screen focused on learning state, not stored record types.
4. Use derived view models when useful, but do not change storage truth for visual convenience.
5. Preview the route in the Codex in-app browser or a local browser.
6. Inspect compactness, hierarchy, overflow, badge clarity, and whether the first screen answers "what should I do next?"
7. Run frontend typecheck/build and relevant Python tests before handoff.

## Default Dashboard

The first screen should show only:

- Active Goal;
- Primary Next Action;
- Open Loops;
- Trust Gaps;
- Ready for Test;
- Recent Activity.

Everything else belongs in deeper pages or an Advanced drawer.

## Visual Style

- compact, calm, academic;
- high information density without dense raw metadata;
- restrained color;
- no decorative gradients, marketing hero sections, social-app styling, or chatbot framing;
- cards only for learning-state summaries and workflow panels;
- details and raw records behind disclosure controls.

## Prompt and Provider UX

API mode is the default interaction when a provider is configured. Prompt mode remains the fallback and must work without any API keys. Even in API mode, never send data automatically: the learner must click "Run with API" after seeing compact context metadata. Use small mode badges instead of large warnings:

- API mode: selected context only;
- Prompt mode: nothing is sent.

Provider settings, raw context previews, event logs, indexes, raw YAML, and AI run artifacts are advanced material.

## Bilingual UI

The Web UI supports English and Simplified Chinese. Translate interface labels, navigation, page titles, short helper text, mode labels, empty states, and buttons. Do not translate user records such as claim text, reference titles, goal text, or session content.

Keep the language switch in the sidebar footer. Store the preference locally.

## Hard Boundaries

Do not add AI API calls as a default path. Do not build a knowledge graph. Do not turn references or Deep Research into a knowledge base. Do not expose all local data on the dashboard.

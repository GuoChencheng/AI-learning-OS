# Web UI Design

`ai-learning-os` Web UI is a local learning cockpit over transparent YAML and Markdown files.

It is not an encyclopedia, note browser, AI chatbot, or knowledge graph. The interface centers learning state:

- active goal and why it matters;
- deterministic next actions;
- open claims and epistemic status;
- derivation trust gaps;
- A/B/C positioning relative to the active goal;
- classification policies as goal-derived learning strategy;
- references as durable source entries;
- visual resource metadata and why a visual is needed;
- context pack generation for Codex/AI-agent work;
- test-mode readiness;
- copyable prompts for external AI tools.

## Architecture

- Python local HTTP server: `ailearn.web_server`
- API router: `ailearn.web_api`
- Frontend: Vite + React + TypeScript + Tailwind
- Data source: the same `data/` folder used by the CLI
- Markdown/math: `react-markdown`, GFM, `remark-math`, KaTeX

No required AI API calls, authentication, remote database, or static knowledge graph are added. Optional provider runs are explicit connected-mode actions.

## Pages

- Learning Cockpit: active goal, next actions, open claims, derivation gaps, ready tests, sessions, references.
- Goals: create goals, set active goal, generate goal intake and Deep Research prompts.
- Deep Research & References: view imports, generate extraction prompts, manage durable references.
- Positioning: inspect and edit A/B/C positioning, tool role, internalization, revisit triggers.
- Policies: inspect the current goal-derived classification language when exposed in UI/API.
- Claims: verify student-generated claims with status, epistemic status, caveats, and boundaries.
- Derivation Trust: track user-derived steps, AI-hinted steps, and untrusted gaps.
- Sessions: lightweight learning footprints with optional learning state and references.
- Method Router: select a learning state and generate method suggestions/prompts.
- Test Mode: manage tests and A0-A4 internalization pressure.
- Weekly Review: generate and inspect local Markdown reviews.
- Settings / Providers: show prompt-only status, configured providers, no key values, provider test actions, and connected-mode privacy warning.
- Visuals and Context Packs: lightweight metadata/API support; avoid turning the cockpit into a media database or file browser.

## Visual System

The UI uses compact panels, dense tables, restrained badges, high-contrast text, and minimal color. Cards frame records and workflow panels, not world knowledge. Formula-heavy Markdown is rendered with KaTeX.

## PDF / References

References display URL or local path clearly. PDF paths use the browser's embedded PDF support when available. Annotation and PDF.js-level tooling are intentionally out of scope for this phase.

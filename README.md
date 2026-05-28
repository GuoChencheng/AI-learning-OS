# AI Learning OS

`ai-learning-os` is a local-first AI-native learning state manager.

It stores learning state, not world knowledge.

## What It Is

The system helps a learner track:

- goals and current learning depth;
- dynamic A/B/C knowledge positioning;
- learner-generated claims and epistemic status;
- derivation trust;
- test-mode/internalization evidence;
- distinctions, misconceptions, temporal traces, references, reviews, and copyable prompts.

Core loop:

```text
Goal -> Position -> Claim -> Verify -> Derivation Trust -> Test -> Review
```

## What It Is Not

It is not a knowledge base, static knowledge graph, note summarizer, hosted web product, or AI tutor clone. It does not store encyclopedic AI notes by default.

## Local-First Philosophy

Records are transparent YAML, Markdown, and JSONL files. The local Web UI is a learning cockpit over the same files used by the CLI.

Prompt-only mode is the default. It sends no data anywhere.

Optional connected mode supports user-provided providers, but only after explicit user action and only with selected prompts or context packs.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cd web && npm ci && npm run build
```

## Quickstart

```bash
learn init .
learn goal create --title "Quantum mechanics" --main-goal "Build reliable perturbation theory intuition"
learn position add density_matrix --position B_knowledge_positioning --tool-role core_tool --reason "Orient mixed-state problems"
learn claim add "Perturbation theory can be seen as a low-order expansion of effective theory."
learn derivation add nondegenerate_perturbation_theory --importance core_tool --result-to-trust "First-order energy correction"
learn prompt verify-claim <claim_id>
learn review weekly
learn validate
```

## Web UI

```bash
learn ui
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

For frontend development:

```bash
learn ui --dev
cd web && npm run dev
```

The Vite dev server proxies `/api` to the Python local server at `127.0.0.1:8765`.

## AI Context Packs

AI agents and providers should not read all local data by default.

```bash
learn index refresh
learn context build --task verify_claim --id <claim_id>
learn prompt verify-claim <claim_id> --with-context
```

Context packs are compact, task-specific Markdown files under `data/context_packs/`.

## Optional BYO API Mode

Copy the example config locally:

```bash
cp config.example.yaml config.yaml
export OPENROUTER_API_KEY="..."
learn provider list
learn provider test openrouter
learn ai run-prompt --provider openrouter --prompt-file prompt.md
learn ai run-context --provider openrouter --context-pack data/context_packs/example.md
```

`config.yaml` and `.env` are ignored by Git. API keys should live in environment variables.

AI outputs are saved under `data/ai_runs/` as review artifacts. They are not automatically applied to claims, derivations, positioning decisions, or tests.

## Privacy Model

- Prompt-only mode sends no data.
- Connected mode sends only the selected prompt/context after explicit action.
- No telemetry.
- No cloud sync.
- No authentication or remote database.
- Private `data/` is ignored by default.

See [PRIVACY.md](PRIVACY.md), [docs/privacy_model.md](docs/privacy_model.md), and [docs/ai_context_protocol.md](docs/ai_context_protocol.md).

## Public Example

See [examples/qm_for_topological_order](examples/qm_for_topological_order) for public-safe sample learning-state records.

## Developer Checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall src
.venv/bin/learn validate
cd web && npm run typecheck && npm run build
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Keep the project local-first and learning-state focused.

# Contributing

Thanks for helping improve `ai-learning-os`.

## Project Boundaries

This project stores learning state, not world knowledge. Contributions should preserve these boundaries:

- no static knowledge graph;
- no cloud sync;
- no required AI API keys;
- no telemetry;
- no default upload of learner data;
- no AI output stored as truth automatically.

## Development Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cd web && npm ci && npm run build
```

## Checks

Run before opening a pull request:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall src
.venv/bin/learn validate
cd web && npm run typecheck && npm run build
```

Provider tests must use mocks unless the test is explicitly skipped without local credentials.

## Pull Requests

Keep PRs small and state which learning workflow is affected. Include tests for schema, storage, prompt generation, provider behavior, or UI/API behavior as appropriate.

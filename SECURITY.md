# Security Policy

## Reporting Vulnerabilities

Please report security issues privately through the repository security advisory flow when available. Do not post API keys, local config files, private learning records, or reference files in public issues.

## Local-First Assumptions

`ai-learning-os` is designed for local use:

- local YAML, Markdown, and JSONL files are the source of truth;
- prompt-only mode sends no data to any provider;
- connected mode is optional and must be explicitly triggered by the user;
- provider credentials should live in environment variables, not repository files.

## Secrets

Never commit:

- `.env`;
- `config.yaml`;
- real API keys;
- private `data/` records;
- private PDFs, notes, or Deep Research reports.

If a secret is accidentally committed, rotate it immediately.

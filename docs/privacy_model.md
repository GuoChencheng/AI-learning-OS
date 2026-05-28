# Privacy Model

`ai-learning-os` uses transparent local files.

## Local Files

Source-of-truth learning state lives under `data/`:

- YAML snapshot records;
- Markdown sessions and reviews;
- JSONL event logs;
- context packs;
- AI run artifacts.

For public repositories, `data/` should stay ignored. Use `examples/` for public-safe sample records.

## Prompt-Only Default

Prompt-only mode sends no data anywhere. It only prints or displays copyable prompts.

## Context Packs

Context packs are explicit, task-specific selections. They prevent agents and providers from reading or sending all local data by default.

## Connected Mode

Connected mode sends only:

- an explicit prompt file; or
- an explicit context pack; or
- a generated prompt the user chooses to run.

It does not send raw references or all sessions unless those are deliberately included in the selected context.

## AI Run Artifacts

Responses are stored under `data/ai_runs/` as review artifacts. They are not automatically applied to learner records and are not treated as truth.

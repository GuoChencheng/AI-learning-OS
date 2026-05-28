# Privacy

`ai-learning-os` is local-first.

## Prompt-Only Mode

Prompt-only mode is the default. The app generates copyable prompts and sends nothing to any AI provider.

## Connected Mode

Connected mode is optional. It sends only the selected prompt file or selected context pack to the provider configured by the user.

Before sending, the CLI shows:

- provider;
- model;
- context size;
- detected record ids;
- detected reference ids;
- whether raw sessions are included;
- whether raw references are included.

The user must confirm unless `--yes` is passed.

## Local Data

Learning records, references, sessions, event logs, context packs, reviews, and AI run artifacts stay in local files. The project does not include telemetry or cloud sync.

## AI Outputs

AI outputs are saved as artifacts under `data/ai_runs/`. They are not automatically applied to claims, derivations, positioning decisions, or tests. The learner must review and explicitly update records.

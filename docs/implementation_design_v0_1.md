# AI Learn OS Implementation Design v0.1

The v0.1 product is a ChatGPT-style learning operating system.

Users interact through a single conversation surface. Each `/api/chat` request runs through eight structured agents: Request Intake, Project Resolver, Context Extractor, Context Pack Builder, State Judge, Module Router, Answer Composer, and State Writer.

Every turn produces:

- answer text;
- suggested next action;
- pipeline trace;
- state updates for claims, distinctions, temporal traces, and review triggers.

The `/api/run-next` endpoint reads the current learning state and chooses one highest-value action in priority order: due review trigger, repeated misconception, unverified no-AI internalization, current goal next action, unresolved recent question, then new knowledge progress.

The UI keeps complexity out of the main screen. The right drawer exposes projects, project settings, system settings, and learning state.

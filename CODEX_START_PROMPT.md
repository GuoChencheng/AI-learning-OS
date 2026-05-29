# Codex Start Prompt Status

The old CLI-first Codex prompt is deprecated.

New development must target AI Learn OS:

- ChatGPT-style Web UI as the primary product surface;
- `/api/chat` and `/api/run-next` through the Orchestrator;
- structured Agent outputs validated by Pydantic;
- database-backed learning state with reversible state updates;
- `FakeModelGateway` for tests and OpenAI-compatible providers for configured runs.

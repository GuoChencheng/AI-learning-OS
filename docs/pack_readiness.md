# Pack Readiness

Target path:

```text
download project
-> install backend and frontend dependencies
-> optionally configure OpenAI-compatible API key
-> seed or create a learning project
-> start a basic automated AI learning loop
```

## Setup Path

Backend:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Frontend:

```bash
cd web
npm install
```

Run local API and UI:

```bash
.venv/bin/learn ui --dev
```

`learn ui --dev` starts the API/static server and the Vite frontend dev server in one terminal. Open `http://127.0.0.1:8765` for the built UI or `http://127.0.0.1:5173` for Vite.

## API Key Path

The app runs without a real key by using `FakeModelGateway` / deterministic fallback. For real model-backed answers, set:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.deepseek.com"
export AI_LEARN_FAST_MODEL="deepseek-v4-flash"
export AI_LEARN_MEDIUM_MODEL="deepseek-v4-flash"
export AI_LEARN_STRONG_MODEL="deepseek-v4-pro"
```

Users can also paste the provider key in `System Settings -> AI Provider`. The key is saved to local `.env.local`, which is ignored by git.

Check what gateway will be used:

```bash
.venv/bin/python scripts/check_ai_path.py
```

The check script reports whether a key is configured but never prints the key.

## Seed Path

Create the focused CFT demo project:

```bash
.venv/bin/python scripts/seed_cft_learning.py
```

The seed creates:

- project `我要学习 CFT`;
- GoalStack;
- a focused original CFT reference with chunks;
- a learner-originated claim;
- a distinction;
- a no-AI knowledge position;
- a derivation trust record;
- a review trigger.

The API endpoint is also available:

```bash
curl -X POST http://127.0.0.1:8765/api/projects/seed/cft -H 'Content-Type: application/json' -d '{}'
```

## Smoke Script

Run a local-safe alpha smoke test against a temporary SQLite database:

```bash
.venv/bin/python scripts/smoke_alpha_pack.py
```

It verifies:

- database initialization;
- CFT seed;
- `/api/chat` with FakeModelGateway;
- `/api/run-next`;
- `/api/projects/:id/learning-summary`;
- Reference chunks entering ContextPack.

It does not require a real API key and does not create a committed local DB.

## Expected First User Flow

```text
Open web app
-> create/select 我要学习 CFT
-> ask: 为什么 2D CFT 可以描述二阶临界点？
-> inspect muted metadata chips for unit/model/reference context
-> click Run Next
-> use Inspector Current Blocker and Next Action
-> perform no-AI/review/distinction/derivation action when prompted
```

## Current Blockers to Smooth Pack Usage

| Blocker | Severity | Notes |
|---|---:|---|
| API key config is env-only | medium | Acceptable for alpha; UI settings should not store secrets yet. |
| CFT seed endpoint is not first-class in UI | medium | API client exists; add a quiet demo project action later. |
| Review complete/fail/skip controls are not exposed | high | Backend exists, but learning loop closure is awkward in UI. |
| No-AI test mode is not visually distinct | high | Backend scoring exists; user needs clear "answer without AI" state. |
| Derivation and distinction assessment are chat-triggered | medium | Works, but designer should add focused cards. |
| Source chunk inspection is minimal | medium | Metadata hover exists; source popover is needed. |
| Revert is partial | medium | State update logs exist; not every table has perfect transaction rollback. |

## Readiness Verdict

The pack is alpha-ready for a technical user:

```text
install -> run -> seed CFT -> chat -> Run Next -> inspect summary
```

It is not yet polished for a non-technical learner because several assessment actions are backend-ready but not exposed as focused UI flows.

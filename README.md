# AI Learn OS

AI Learn OS is a Web-first, API-first learning operating system with a ChatGPT-style learning interface.

The learner chats in a minimal UI. Behind each turn the backend runs the learning loop:

```text
Goal -> Position -> Action -> Thought -> Verify -> Mark -> Handle -> Next Round
```

The system stores learning state, not world knowledge. It tracks claims, distinctions, temporal traces, knowledge positions, derivation trust, review triggers, module runs, and reversible state updates.

## Product Shape

- Frontend: ChatGPT-style conversation, teaching action buttons, run-next button, project switcher, hidden settings/state drawer.
- Backend: API Gateway, Orchestrator, Agent Layer, Data Layer, Model Gateway, State Writer.
- Storage: SQLite for local tests/development, Postgres + pgvector for production deployments.
- Model calls: fast / medium / strong tiers through an OpenAI-compatible gateway. Tests use `FakeModelGateway`.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
docker compose up -d postgres redis
.venv/bin/learn ui
cd web && npm install && npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite proxies `/api` to the Python server on `127.0.0.1:8765`.

The local fallback database is `data/ai_learn_os.sqlite3`. `data/`, `.env`, `config.yaml`, caches, and build outputs are ignored by Git.

## Core API

- `POST /api/chat`
- `POST /api/run-next`
- `GET/POST/PATCH /api/projects`
- `GET/PATCH /api/projects/:id/settings`
- `GET/PATCH /api/system-settings`
- `GET /api/projects/:id/state`
- `POST/GET /api/projects/:id/references`
- `POST /api/state-updates/:id/revert`

See [docs/api.md](docs/api.md).

## Developer Checks

```bash
.venv/bin/python -m compileall src
.venv/bin/python -m pytest -q
cd web && npm run typecheck
cd web && npm run build
```

## Legacy Code

The old CLI/YAML learning-state tools remain as compatibility helpers, but they are no longer the primary product entry. The primary product is the Web/API ChatGPT-style AI Learn OS described in [docs/implementation_design_v0_1.md](docs/implementation_design_v0_1.md).

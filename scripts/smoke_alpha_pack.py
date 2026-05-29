from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(SRC), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ailearn.api.app import create_app
from ailearn.api.testing import TestClient
from ailearn.db.database import Database
from ailearn.db.repository import Repository
from ailearn.model_gateway.fake import FakeModelGateway

from scripts.seed_cft_learning import seed_cft_learning


def run_smoke() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    with TemporaryDirectory(prefix="ai-learn-os-smoke-") as temp_dir:
        try:
            database = Database(f"sqlite:///{Path(temp_dir) / 'alpha-smoke.sqlite3'}")
            database.init()
            repo = Repository(database)
            checks["database_initializes"] = True

            project = seed_cft_learning(repository=repo)
            seeded_state = repo.project_state(project["id"])
            checks["cft_seed_works"] = bool(
                project["name"] == "我要学习 CFT"
                and seeded_state["knowledge_positions"]
                and seeded_state["review_triggers"]
                and repo.list_references(project["id"])
            )

            client = TestClient(create_app(database=database, model_gateway=FakeModelGateway()))
            chat_response = client.post(
                "/api/chat",
                json={
                    "project_id": project["id"],
                    "message": "为什么 2D CFT 可以描述二阶临界点？",
                    "selected_mode": "auto",
                    "button_action": None,
                },
            )
            chat = chat_response.json()
            checks["chat_works"] = chat_response.status_code == 200 and bool(chat.get("answer"))
            context_pack = chat["pipeline_trace"]["steps"][3]["output"]
            checks["reference_chunks_enter_context"] = "Excerpt:" in context_pack.get("reference_context", "")

            run_next_response = client.post("/api/run-next", json={"project_id": project["id"]})
            run_next = run_next_response.json()
            checks["run_next_works"] = run_next_response.status_code == 200 and bool(run_next.get("chosen_module"))

            summary_response = client.get(f"/api/projects/{project['id']}/learning-summary")
            summary = summary_response.json()
            checks["learning_summary_works"] = summary_response.status_code == 200 and "current_blocker" in summary

            return {
                "ok": all(checks.values()),
                "project_id": project["id"],
                "checks": checks,
                "run_next_priority": run_next.get("priority"),
                "current_blocker": summary.get("current_blocker", {}).get("type"),
            }
        except Exception as exc:  # pragma: no cover - CLI diagnostic path
            return {"ok": False, "checks": checks, "error": f"{exc.__class__.__name__}: {exc}"}


def main() -> None:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

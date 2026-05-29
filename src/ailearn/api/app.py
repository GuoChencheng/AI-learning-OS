from __future__ import annotations

import os
import json
from typing import Any
from urllib.parse import unquote

from ailearn.db.database import Database
from ailearn.db.repository import Repository
from ailearn.model_gateway.base import ModelGateway
from ailearn.model_gateway.fake import FakeModelGateway
from ailearn.orchestrator.chat_orchestrator import ChatOrchestrator
from ailearn.orchestrator.run_next_orchestrator import RunNextOrchestrator
from ailearn.references.chunking import chunk_text
from ailearn.references.extract import extract_reference_text


class AILearnOSApp:
    def __init__(self, database: Database, model_gateway: ModelGateway | None = None) -> None:
        self.database = database
        self.repository = Repository(database)
        self.model_gateway = model_gateway or FakeModelGateway()

    def handle(self, method: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | list[dict[str, Any]]]:
        try:
            return self._handle(method, path.split("?", 1)[0], payload)
        except KeyError as exc:
            return 404, {"error": f"Not found: {exc.args[0]}"}
        except ValueError as exc:
            return 400, {"error": str(exc)}

    def _handle(self, method: str, path: str, payload: dict[str, Any]) -> tuple[int, Any]:
        parts = [unquote(part) for part in path.strip("/").split("/") if part]
        if parts[:1] != ["api"]:
            return 404, {"error": "API path required."}

        if method == "POST" and parts == ["api", "chat"]:
            result = ChatOrchestrator(self.repository, self.model_gateway).run(
                payload.get("project_id"),
                payload.get("message", ""),
                payload.get("selected_mode", "auto"),
                payload.get("button_action"),
            )
            return 200, result

        if method == "POST" and parts == ["api", "run-next"]:
            return 200, RunNextOrchestrator(self.repository, self.model_gateway).run(payload["project_id"])

        if parts == ["api", "projects"] and method == "GET":
            return 200, {"items": self.repository.list_projects()}
        if parts == ["api", "projects"] and method == "POST":
            if not payload.get("name"):
                raise ValueError("Project name is required.")
            return 200, self.repository.create_project(payload)
        if len(parts) == 3 and parts[:2] == ["api", "projects"]:
            project_id = parts[2]
            if method == "GET":
                project = self.repository.get_project(project_id)
                if not project:
                    raise KeyError(project_id)
                return 200, project
            if method == "PATCH":
                return 200, self.repository.update_project(project_id, payload)

        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "settings":
            project_id = parts[2]
            if method == "GET":
                return 200, self.repository.ensure_project_settings(project_id)
            if method == "PATCH":
                return 200, self.repository.update_project_settings(project_id, payload)

        if len(parts) == 5 and parts[:2] == ["api", "projects"] and parts[3] == "learning-units" and parts[4] == "active" and method == "GET":
            return 200, {"item": self.repository.get_active_learning_unit(parts[2])}
        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "learning-units" and method == "GET":
            return 200, {"items": self.repository.list_learning_units(parts[2])}
        if len(parts) == 6 and parts[:2] == ["api", "projects"] and parts[3] == "learning-units" and method == "POST":
            project_id = parts[2]
            unit_id = parts[4]
            unit = self.repository.get_by_id("learning_units", unit_id)
            if not unit or unit.get("project_id") != project_id:
                raise KeyError(unit_id)
            if parts[5] == "close":
                return 200, self.repository.close_learning_unit(unit_id, payload.get("reason", "user_closed"))
            if parts[5] == "refresh-context":
                snapshot = unit.get("context_snapshot_json") if isinstance(unit.get("context_snapshot_json"), dict) else {}
                return 200, self.repository.update_learning_unit(unit_id, {"context_snapshot_json": {**snapshot, "refresh_requested": True}})

        if parts == ["api", "system-settings"]:
            if method == "GET":
                return 200, self.repository.get_system_settings()
            if method == "PATCH":
                return 200, self.repository.update_system_settings(payload)

        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "state" and method == "GET":
            return 200, self.repository.project_state(parts[2])
        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] in {
            "claims",
            "distinctions",
            "review-triggers",
            "knowledge-positions",
        }:
            table = {
                "claims": "claims",
                "distinctions": "distinctions",
                "review-triggers": "review_triggers",
                "knowledge-positions": "knowledge_positions",
            }[parts[3]]
            if method == "GET":
                if table == "knowledge_positions":
                    items = self.repository.project_state(parts[2])["knowledge_positions"]
                else:
                    items = self.repository.list_by_project(table, parts[2], limit=100)
                return 200, {"items": items}
            if method == "POST" and table == "review_triggers":
                return 200, self.repository.create_review_trigger(parts[2], payload)

        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "references":
            project_id = parts[2]
            if method == "GET":
                return 200, {"items": self.repository.list_references(project_id)}
            if method == "POST":
                text = payload.pop("text", "")
                payload["chunks"] = chunk_text(text) if text else payload.get("chunks", [])
                return 200, self.repository.add_reference(project_id, payload)
        if len(parts) == 5 and parts[:2] == ["api", "projects"] and parts[3] == "references" and parts[4] == "upload" and method == "POST":
            project_id = parts[2]
            text = extract_reference_text(payload.get("filename", payload.get("title", "upload")), payload.get("text", ""), payload.get("content_base64"))
            return 200, self.repository.add_reference(project_id, {**payload, "source_type": payload.get("source_type", "upload"), "chunks": chunk_text(text)})
        if len(parts) == 4 and parts[:2] == ["api", "references"] and parts[3] == "chunks" and method == "GET":
            return 200, {"items": self.repository.list_reference_chunks(parts[2])}

        if len(parts) == 4 and parts[:2] == ["api", "state-updates"] and parts[3] == "revert" and method == "POST":
            return 200, self.repository.revert_state_update(parts[2])

        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "research-report" and method == "POST":
            state = self.repository.project_state(parts[2])
            return 200, {
                "report": "# Project Report\n\n"
                f"- Claims: {len(state['claims'])}\n"
                f"- Distinctions: {len(state['distinctions'])}\n"
                f"- Review triggers: {len(state['review_triggers'])}\n"
            }

        return 404, {"error": f"Unknown endpoint: {method} {path}"}


def create_core_app(database: Database | None = None, model_gateway: ModelGateway | None = None) -> AILearnOSApp:
    db = database or Database(os.getenv("AI_LEARN_DATABASE_URL", "sqlite:///data/ai_learn_os.sqlite3"))
    db.init()
    return AILearnOSApp(db, model_gateway=model_gateway)


def create_app(database: Database | None = None, model_gateway: ModelGateway | None = None) -> Any:
    core = create_core_app(database=database, model_gateway=model_gateway)
    try:
        return create_fastapi_app(core)
    except ModuleNotFoundError:
        return core


def create_fastapi_app(core: AILearnOSApp) -> Any:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    app = FastAPI(title="AI Learn OS API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def dispatch(request: Request, api_path: str) -> JSONResponse:
        payload = await _read_json_payload(request)
        status, data = core.handle(request.method, f"/api/{api_path}", payload)
        return JSONResponse(status_code=status, content=data)

    @app.api_route("/api/projects", methods=["GET", "POST", "OPTIONS"])
    async def projects_route(request: Request) -> JSONResponse:
        return await dispatch(request, "projects")

    @app.api_route("/api/chat", methods=["POST", "OPTIONS"])
    async def chat_route(request: Request) -> JSONResponse:
        return await dispatch(request, "chat")

    @app.api_route("/api/run-next", methods=["POST", "OPTIONS"])
    async def run_next_route(request: Request) -> JSONResponse:
        return await dispatch(request, "run-next")

    @app.api_route("/api/system-settings", methods=["GET", "PATCH", "OPTIONS"])
    async def system_settings_route(request: Request) -> JSONResponse:
        return await dispatch(request, "system-settings")

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"])
    async def api_route(path: str, request: Request) -> JSONResponse:
        return await dispatch(request, path)

    app.state.ai_learn_core = core
    return app


async def _read_json_payload(request: Any) -> dict[str, Any]:
    if request.method not in {"POST", "PATCH", "PUT"}:
        return {}
    body = await request.body()
    if not body:
        return {}
    try:
        value = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .database import Database


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


JSON_FIELDS = {
    "project_settings": {"enabled_modules"},
    "references": {"metadata"},
    "reference_chunks": {"metadata", "embedding"},
    "context_packs": {"known_confusions", "must_respect_constraints"},
    "derivation_trust_records": {"assumptions", "key_steps", "done_by_user", "hinted_by_ai", "untrusted_steps", "failure_conditions"},
}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


class Repository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.database.connect() as connection:
            connection.execute(sql, params)

    def _row(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(sql, params).fetchone()
        return self._decode(dict(row)) if row else None

    def _rows(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._decode(dict(row)) for row in rows]

    def _insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        encoded = self._encode(table, data)
        keys = list(encoded)
        placeholders = ", ".join("?" for _ in keys)
        columns = ", ".join(keys)
        with self.database.connect() as connection:
            connection.execute(
                f"INSERT INTO {_q(table)} ({columns}) VALUES ({placeholders})",
                tuple(encoded[key] for key in keys),
            )
        return self.get_by_id(table, data["id"]) or data

    def _update(self, table: str, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        encoded = self._encode(table, data)
        assignments = ", ".join(f"{key} = ?" for key in encoded)
        with self.database.connect() as connection:
            connection.execute(f"UPDATE {_q(table)} SET {assignments} WHERE id = ?", tuple(encoded.values()) + (item_id,))
        return self.get_by_id(table, item_id) or {"id": item_id, **data}

    def _encode(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        fields = JSON_FIELDS.get(table, set())
        encoded: dict[str, Any] = {}
        for key, value in data.items():
            if key in fields and not isinstance(value, str):
                encoded[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                encoded[key] = 1 if value else 0
            else:
                encoded[key] = value
        return encoded

    def _decode(self, row: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(row)
        for key, value in list(decoded.items()):
            if isinstance(value, str) and value and (value[0] == "{" or value[0] == "["):
                try:
                    decoded[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return decoded

    def get_by_id(self, table: str, item_id: str) -> dict[str, Any] | None:
        return self._row(f"SELECT * FROM {_q(table)} WHERE id = ?", (item_id,))

    def list_by_project(self, table: str, project_id: str, limit: int | None = None, newest: bool = True) -> list[dict[str, Any]]:
        order = "DESC" if newest else "ASC"
        sql = f"SELECT * FROM {_q(table)} WHERE project_id = ? ORDER BY created_at {order}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self._rows(sql, (project_id,))

    def ensure_user(self) -> dict[str, Any]:
        existing = self._row("SELECT * FROM users LIMIT 1")
        if existing:
            return existing
        now = now_iso()
        return self._insert("users", {"id": "user_local", "name": "Local Learner", "created_at": now, "updated_at": now})

    def ensure_system_settings(self) -> dict[str, Any]:
        existing = self.get_by_id("system_settings", "system_default")
        if existing:
            return existing
        now = now_iso()
        return self._insert("system_settings", {"id": "system_default", "created_at": now, "updated_at": now})

    def get_system_settings(self) -> dict[str, Any]:
        return self.ensure_system_settings()

    def update_system_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        self.ensure_system_settings()
        data = {**data, "updated_at": now_iso()}
        return self._update("system_settings", "system_default", data)

    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        user = self.ensure_user()
        now = now_iso()
        project = self._insert(
            "projects",
            {
                "id": data.get("id") or new_id("proj"),
                "user_id": data.get("user_id") or user["id"],
                "name": data["name"],
                "description": data.get("description", ""),
                "mode": data.get("mode", "general"),
                "status": data.get("status", "active"),
                "created_at": now,
                "updated_at": now,
            },
        )
        self.ensure_project_settings(project["id"])
        self.create_goal_stack(
            project["id"],
            {
                "main_goal": data.get("description") or data["name"],
                "stage_goal": data.get("stage_goal", "Clarify the current learning question."),
                "current_focus": data.get("current_focus", data["name"]),
                "next_action": data.get("next_action", "Ask a question or run the next learning action."),
            },
        )
        return project

    def ensure_default_project(self) -> dict[str, Any]:
        existing = self._row("SELECT * FROM projects WHERE status = 'active' ORDER BY created_at ASC LIMIT 1")
        return existing or self.create_project({"name": "Default Learning Project", "description": "General AI Learn OS project"})

    def list_projects(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM projects ORDER BY updated_at DESC")

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.get_by_id("projects", project_id)

    def update_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        data = {**data, "updated_at": now_iso()}
        return self._update("projects", project_id, data)

    def ensure_project_settings(self, project_id: str) -> dict[str, Any]:
        existing = self._row("SELECT * FROM project_settings WHERE project_id = ?", (project_id,))
        if existing:
            return existing
        now = now_iso()
        return self._insert("project_settings", {"id": new_id("pset"), "project_id": project_id, "created_at": now, "updated_at": now})

    def update_project_settings(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        settings = self.ensure_project_settings(project_id)
        data = {**data, "updated_at": now_iso()}
        return self._update("project_settings", settings["id"], data)

    def create_goal_stack(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        payload = {
            "id": data.get("id") or new_id("goal"),
            "project_id": project_id,
            "main_goal": data.get("main_goal", ""),
            "stage_goal": data.get("stage_goal", ""),
            "transfer_goal": data.get("transfer_goal", ""),
            "external_goal": data.get("external_goal", ""),
            "conflict_goal": data.get("conflict_goal", ""),
            "current_focus": data.get("current_focus", ""),
            "next_action": data.get("next_action", ""),
            "version": data.get("version", 1),
            "created_at": now,
            "updated_at": now,
        }
        return self._insert("goal_stacks", payload)

    def list_goal_stacks(self, project_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        return self.list_by_project("goal_stacks", project_id, limit=limit)

    def add_message(self, project_id: str, role: str, content: str, selected_mode: str | None = None, button_action: str | None = None) -> dict[str, Any]:
        now = now_iso()
        return self._insert(
            "messages",
            {
                "id": new_id("msg"),
                "project_id": project_id,
                "role": role,
                "content": content,
                "selected_mode": selected_mode,
                "button_action": button_action,
                "created_at": now,
            },
        )

    def add_context_pack(self, project_id: str, message_id: str, pack: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        return self._insert("context_packs", {"id": new_id("ctx"), "project_id": project_id, "message_id": message_id, "created_at": now, **pack})

    def add_module_run(self, project_id: str, message_id: str | None, module_name: str, input_summary: str, output_summary: str, model_tier: str = "fast", latency_ms: int = 0) -> dict[str, Any]:
        return self._insert(
            "module_runs",
            {
                "id": new_id("run"),
                "project_id": project_id,
                "message_id": message_id,
                "module_name": module_name,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "model_tier": model_tier,
                "latency_ms": latency_ms,
                "created_at": now_iso(),
            },
        )

    def add_reference(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        reference = self._insert(
            "references",
            {
                "id": data.get("id") or new_id("ref"),
                "project_id": project_id,
                "title": data["title"],
                "source_type": data.get("source_type", "manual"),
                "reliability_level": data.get("reliability_level", "uncertain"),
                "scope": data.get("scope", ""),
                "metadata": data.get("metadata", {}),
                "created_at": now,
            },
        )
        for index, chunk in enumerate(data.get("chunks", []), start=1):
            self._insert(
                "reference_chunks",
                {
                    "id": new_id("chunk"),
                    "reference_id": reference["id"],
                    "chunk_text": chunk,
                    "embedding": data.get("embedding"),
                    "page_number": data.get("page_number"),
                    "section_title": data.get("section_title") or f"Chunk {index}",
                    "metadata": {"index": index},
                },
            )
        return reference

    def list_references(self, project_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        return self.list_by_project("references", project_id, limit=limit)

    def list_reference_chunks(self, reference_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM reference_chunks WHERE reference_id = ? ORDER BY section_title ASC", (reference_id,))

    def project_state(self, project_id: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "claims": self.list_by_project("claims", project_id, limit=50),
            "distinctions": self.list_by_project("distinctions", project_id, limit=50),
            "temporal_traces": self.list_by_project("temporal_traces", project_id, limit=50),
            "knowledge_positions": self._rows("SELECT * FROM knowledge_positions WHERE project_id = ? ORDER BY updated_at DESC", (project_id,)),
            "derivation_trust_records": self.list_by_project("derivation_trust_records", project_id, limit=50),
            "review_triggers": self.list_by_project("review_triggers", project_id, limit=50),
            "module_runs": self.list_by_project("module_runs", project_id, limit=50),
        }

    def create_review_trigger(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": data.get("id") or new_id("rev"),
            "project_id": project_id,
            "target": data["target"],
            "trigger_reason": data["trigger_reason"],
            "review_type": data["review_type"],
            "scheduled_time": data["scheduled_time"],
            "success_criteria": data["success_criteria"],
            "status": data.get("status", "pending"),
            "created_at": now_iso(),
        }
        return self._insert("review_triggers", payload)

    def apply_state_writer_output(self, project_id: str, message_id: str | None, output: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        created: dict[str, list[dict[str, Any]]] = {"claims": [], "distinctions": [], "temporal_traces": [], "review_triggers": []}
        for claim in output.get("new_claims", []):
            created["claims"].append(
                self._insert(
                    "claims",
                    {
                        "id": new_id("claim"),
                        "project_id": project_id,
                        "source_message_id": message_id,
                        "status": "active",
                        "created_at": now,
                        "updated_at": now,
                        **claim,
                    },
                )
            )
        for distinction in output.get("new_distinctions", []):
            created["distinctions"].append(
                self._insert("distinctions", {"id": new_id("dist"), "project_id": project_id, "created_at": now, "updated_at": now, **distinction})
            )
        trace = output["new_temporal_trace"]
        created["temporal_traces"].append(
            self._insert("temporal_traces", {"id": new_id("trace"), "project_id": project_id, "created_at": now, **trace})
        )
        for trigger in output.get("review_triggers", []):
            created["review_triggers"].append(self.create_review_trigger(project_id, trigger))
        for position in output.get("knowledge_position_updates", []):
            self._insert("knowledge_positions", {"id": new_id("kp"), "project_id": project_id, "updated_at": now, **position})
        for derivation in output.get("derivation_trust_updates", []):
            self._insert("derivation_trust_records", {"id": new_id("der"), "project_id": project_id, "created_at": now, "updated_at": now, **derivation})
        log = self._insert(
            "state_update_logs",
            {
                "id": new_id("upd"),
                "project_id": project_id,
                "message_id": message_id,
                "update_type": "state_writer",
                "payload_json": json.dumps({"created": created}, ensure_ascii=False),
                "status": "applied",
                "created_at": now,
            },
        )
        return {**created, "log_id": log["id"]}

    def revert_state_update(self, update_id: str) -> dict[str, Any]:
        log = self.get_by_id("state_update_logs", update_id)
        if not log:
            raise KeyError(update_id)
        payload = json.loads(log["payload_json"]) if isinstance(log["payload_json"], str) else log["payload_json"]
        created = payload.get("created", {})
        now = now_iso()
        for claim in created.get("claims", []):
            self._update("claims", claim["id"], {"status": "deprecated", "updated_at": now})
        for trigger in created.get("review_triggers", []):
            self._update("review_triggers", trigger["id"], {"status": "skipped"})
        return self._update("state_update_logs", update_id, {"status": "reverted"})

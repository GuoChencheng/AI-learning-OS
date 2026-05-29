from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
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
    "learning_units": {"context_snapshot_json"},
    "learning_unit_turns": {"user_state_signal_json"},
    "derivation_trust_records": {"assumptions", "key_steps", "done_by_user", "hinted_by_ai", "untrusted_steps", "failure_conditions"},
    "misconception_records": {"related_claim_ids_json", "related_distinction_ids_json"},
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

    def get_active_learning_unit(self, project_id: str) -> dict[str, Any] | None:
        return self._row(
            "SELECT * FROM learning_units WHERE project_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
            (project_id,),
        )

    def create_learning_unit(
        self,
        project_id: str,
        method: str,
        topic: str,
        start_message_id: str | None = None,
        context_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = now_iso()
        return self._insert(
            "learning_units",
            {
                "id": new_id("unit"),
                "project_id": project_id,
                "status": "active",
                "method": method,
                "topic": topic or "current learning topic",
                "start_message_id": start_message_id,
                "last_message_id": start_message_id,
                "context_snapshot_json": context_snapshot or {},
                "unit_summary": "",
                "turn_count": 0,
                "close_reason": None,
                "created_at": now,
                "updated_at": now,
                "closed_at": None,
            },
        )

    def update_learning_unit(self, unit_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        return self._update("learning_units", unit_id, {**patch, "updated_at": now_iso()})

    def close_learning_unit(self, unit_id: str, reason: str) -> dict[str, Any]:
        unit = self.get_by_id("learning_units", unit_id)
        if not unit:
            raise KeyError(unit_id)
        summary = unit.get("unit_summary") or f"Closed {unit.get('method', 'learning')} unit on {unit.get('topic', 'current topic')}."
        return self._update(
            "learning_units",
            unit_id,
            {
                "status": "closed",
                "close_reason": reason,
                "unit_summary": summary,
                "updated_at": now_iso(),
                "closed_at": now_iso(),
            },
        )

    def add_learning_unit_turn(
        self,
        unit_id: str,
        project_id: str,
        message_id: str | None,
        role: str,
        turn_summary: str,
        user_state_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = now_iso()
        turn = self._insert(
            "learning_unit_turns",
            {
                "id": new_id("uturn"),
                "unit_id": unit_id,
                "project_id": project_id,
                "message_id": message_id,
                "role": role,
                "turn_summary": turn_summary,
                "user_state_signal_json": user_state_signal or {},
                "created_at": now,
            },
        )
        unit = self.get_by_id("learning_units", unit_id)
        if unit:
            self._update(
                "learning_units",
                unit_id,
                {
                    "last_message_id": message_id,
                    "turn_count": int(unit.get("turn_count") or 0) + 1,
                    "updated_at": now,
                },
            )
        return turn

    def list_learning_unit_turns(self, unit_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._rows(
            "SELECT * FROM learning_unit_turns WHERE unit_id = ? ORDER BY created_at DESC LIMIT ?",
            (unit_id, int(limit)),
        )
        return list(reversed(rows))

    def list_learning_units(self, project_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT * FROM learning_units WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?",
            (project_id, int(limit)),
        )

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
            "misconception_records": self.list_by_project("misconception_records", project_id, limit=50),
        }

    def add_distinction(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        return self._insert(
            "distinctions",
            {
                "id": data.get("id") or new_id("dist"),
                "project_id": project_id,
                "status": data.get("status", "needs_test"),
                "confusion_count": int(data.get("confusion_count") or 0),
                "last_test_result": data.get("last_test_result"),
                "next_distinction_test_at": data.get("next_distinction_test_at"),
                "created_at": now,
                "updated_at": now,
                **{key: value for key, value in data.items() if key not in {"id", "project_id"}},
            },
        )

    def add_derivation_trust_record(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        return self._insert(
            "derivation_trust_records",
            {
                "id": data.get("id") or new_id("der"),
                "project_id": project_id,
                "result_or_tool": data["result_or_tool"],
                "assumptions": data.get("assumptions", []),
                "key_steps": data.get("key_steps", []),
                "done_by_user": data.get("done_by_user", []),
                "hinted_by_ai": data.get("hinted_by_ai", []),
                "untrusted_steps": data.get("untrusted_steps", []),
                "failure_conditions": data.get("failure_conditions", []),
                "no_ai_reconstruction_status": data.get("no_ai_reconstruction_status", "not_started"),
                "next_rederive_time": data.get("next_rederive_time"),
                "trust_status": data.get("trust_status", "untrusted"),
                "last_step_assessment": data.get("last_step_assessment"),
                "created_at": now,
                "updated_at": now,
            },
        )

    def update_knowledge_position_assessment(
        self,
        project_id: str,
        concept: str,
        previous_level: str,
        new_level: str,
        result: str,
        evidence_text: str,
        reason: str,
    ) -> dict[str, Any]:
        existing = self._row("SELECT * FROM knowledge_positions WHERE project_id = ? AND concept = ? ORDER BY updated_at DESC LIMIT 1", (project_id, concept))
        now = now_iso()
        payload = {
            "concept": concept,
            "layer": existing.get("layer", "no_ai_internalization") if existing else "no_ai_internalization",
            "reason": reason,
            "target_level": existing.get("target_level", "A3") if existing else "A3",
            "current_level": new_level,
            "review_needed": 0 if result == "passed" and new_level in {"A3", "A4"} else 1,
            "last_assessed_at": now,
            "last_assessment_result": result,
            "assessment_evidence": evidence_text,
            "updated_at": now,
        }
        if existing:
            return self._update("knowledge_positions", existing["id"], payload)
        return self._insert("knowledge_positions", {"id": new_id("kp"), "project_id": project_id, **payload})

    def update_derivation_trust_assessment(self, record_id: str, assessment: dict[str, Any]) -> dict[str, Any]:
        record = self.get_by_id("derivation_trust_records", record_id)
        if not record:
            raise KeyError(record_id)
        trust_status = "trusted" if assessment.get("no_ai_reconstruction_status") in {"passed", "trusted"} and not assessment.get("untrusted_steps") else "partial"
        patch = {
            "done_by_user": _merge_list(record.get("done_by_user", []), assessment.get("done_by_user", [])),
            "hinted_by_ai": _merge_list(record.get("hinted_by_ai", []), assessment.get("hinted_by_ai", [])),
            "untrusted_steps": list(assessment.get("untrusted_steps", [])),
            "no_ai_reconstruction_status": assessment.get("no_ai_reconstruction_status", record.get("no_ai_reconstruction_status", "partial")),
            "trust_status": trust_status,
            "last_step_assessment": assessment.get("reason", ""),
            "next_rederive_time": assessment.get("next_rederive_time", record.get("next_rederive_time")),
            "updated_at": now_iso(),
        }
        return self._update("derivation_trust_records", record_id, patch)

    def update_distinction_assessment(self, distinction_id: str, assessment: dict[str, Any]) -> dict[str, Any]:
        distinction = self.get_by_id("distinctions", distinction_id)
        if not distinction:
            raise KeyError(distinction_id)
        confusion_count = int(distinction.get("confusion_count") or 0) + int(assessment.get("confusion_count_delta") or 0)
        return self._update(
            "distinctions",
            distinction_id,
            {
                "status": assessment.get("status", distinction.get("status", "needs_test")),
                "confusion_count": confusion_count,
                "last_test_result": assessment.get("evidence_text", ""),
                "next_distinction_test_at": assessment.get("next_distinction_test_at"),
                "updated_at": now_iso(),
            },
        )

    def update_claim_epistemic_status(self, claim_id: str, assessment: dict[str, Any]) -> dict[str, Any]:
        claim = self.get_by_id("claims", claim_id)
        if not claim:
            raise KeyError(claim_id)
        return self._update(
            "claims",
            claim_id,
            {
                "epistemic_status": assessment.get("epistemic_status", claim.get("epistemic_status")),
                "status": assessment.get("status", claim.get("status")),
                "confidence": assessment.get("confidence", claim.get("confidence")),
                "correction": assessment.get("correction") or assessment.get("caveat") or claim.get("correction"),
                "updated_at": now_iso(),
            },
        )

    def upsert_misconception_record(
        self,
        project_id: str,
        misconception_key: str,
        statement: str,
        related_claim_ids: list[str],
        related_distinction_ids: list[str],
        evidence_text: str,
        next_action: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        existing = self._row(
            "SELECT * FROM misconception_records WHERE project_id = ? AND misconception_key = ? ORDER BY updated_at DESC LIMIT 1",
            (project_id, misconception_key),
        )
        now = now_iso()
        if existing:
            count = int(existing.get("recurrence_count") or 0) + 1
            return self._update(
                "misconception_records",
                existing["id"],
                {
                    "statement": statement,
                    "related_claim_ids_json": _merge_list(existing.get("related_claim_ids_json", []), related_claim_ids),
                    "related_distinction_ids_json": _merge_list(existing.get("related_distinction_ids_json", []), related_distinction_ids),
                    "recurrence_count": count,
                    "severity": _max_severity(existing.get("severity", "medium"), severity, count),
                    "status": "recurring" if count >= 2 else "active",
                    "evidence_text": evidence_text,
                    "next_action": next_action,
                    "updated_at": now,
                },
            )
        return self._insert(
            "misconception_records",
            {
                "id": new_id("misc"),
                "project_id": project_id,
                "misconception_key": misconception_key,
                "statement": statement,
                "related_claim_ids_json": related_claim_ids,
                "related_distinction_ids_json": related_distinction_ids,
                "recurrence_count": 1,
                "severity": severity,
                "status": "active",
                "evidence_text": evidence_text,
                "next_action": next_action,
                "created_at": now,
                "updated_at": now,
            },
        )

    def update_review_trigger_status(self, trigger_id: str, status: str, evidence_text: str = "", failure_reason: str = "", next_retry_time: str | None = None) -> dict[str, Any]:
        trigger = self.get_by_id("review_triggers", trigger_id)
        if not trigger:
            raise KeyError(trigger_id)
        patch = {
            "status": status,
            "result_evidence": evidence_text,
            "failure_reason": failure_reason,
            "next_retry_time": next_retry_time,
            "completed_at": now_iso() if status == "completed" else trigger.get("completed_at"),
        }
        updated = self._update("review_triggers", trigger_id, patch)
        self.log_assessment_update(
            trigger["project_id"],
            None,
            "review_trigger",
            {
                "review_trigger_id": trigger_id,
                "status": status,
                "evidence_text": evidence_text,
                "failure_reason": failure_reason,
                "next_retry_time": next_retry_time,
            },
        )
        if status == "failed" and next_retry_time:
            self.create_review_trigger(
                trigger["project_id"],
                {
                    "target": trigger["target"],
                    "trigger_reason": f"Retry after failed review: {failure_reason or trigger.get('trigger_reason', '')}",
                    "review_type": trigger["review_type"],
                    "scheduled_time": next_retry_time,
                    "success_criteria": trigger["success_criteria"],
                },
            )
        return updated

    def complete_review_trigger(self, trigger_id: str, evidence_text: str = "", result_note: str = "") -> dict[str, Any]:
        return self.update_review_trigger_status(trigger_id, "completed", evidence_text or result_note)

    def fail_review_trigger(self, trigger_id: str, evidence_text: str = "", failure_reason: str = "", next_retry_time: str | None = None) -> dict[str, Any]:
        retry = next_retry_time or (datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        return self.update_review_trigger_status(trigger_id, "failed", evidence_text, failure_reason, retry)

    def skip_review_trigger(self, trigger_id: str, evidence_text: str = "") -> dict[str, Any]:
        return self.update_review_trigger_status(trigger_id, "skipped", evidence_text)

    def log_assessment_update(self, project_id: str, message_id: str | None, update_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "state_update_logs",
            {
                "id": new_id("upd"),
                "project_id": project_id,
                "message_id": message_id,
                "update_type": update_type,
                "payload_json": json.dumps(payload, ensure_ascii=False),
                "status": "applied",
                "created_at": now_iso(),
            },
        )

    def project_learning_summary(self, project_id: str) -> dict[str, Any]:
        state = self.project_state(project_id)
        now = now_iso()
        due_reviews = [
            item for item in state["review_triggers"]
            if item.get("status") in {"pending", "failed"} and str(item.get("scheduled_time", "")) <= now
        ]
        recurring = [item for item in state["misconception_records"] if item.get("status") == "recurring"]
        no_ai_gaps = [
            item for item in state["knowledge_positions"]
            if item.get("layer") == "no_ai_internalization" and item.get("current_level") in {"A0", "A1", "A2"}
        ]
        trust_gaps = [
            item for item in state["derivation_trust_records"]
            if item.get("trust_status") != "trusted" or item.get("untrusted_steps")
        ]
        distinction_gaps = [
            item for item in state["distinctions"]
            if item.get("status", "needs_test") in {"needs_test", "partially_clear", "failed", "needs_retest"}
        ]
        claim_gaps = [
            item for item in state["claims"]
            if item.get("status") in {"active", "wrong", "misleading", "open_question"} or item.get("epistemic_status") in {"wrong", "open_question"}
        ]

        if due_reviews:
            item = due_reviews[0]
            blocker = _blocker("review", item["target"], item.get("trigger_reason", ""), item.get("result_evidence") or item.get("failure_reason") or item.get("success_criteria", ""), [item["id"]])
            action = _next_action("review_point_runner", "处理到期回看点", "Pending or failed review triggers have priority.", "Answer the review prompt without AI, then complete/fail/skip it.")
        elif recurring:
            item = recurring[0]
            blocker = _blocker("misconception", item["statement"], "Recurring misconception blocks reliable transfer.", item.get("evidence_text", ""), [item["id"]])
            action = _next_action("flawed_interpretation_critic", "审查反复误区", item.get("next_action", ""), "State the wrong pattern, then repair it with a distinction test.")
        elif no_ai_gaps:
            item = no_ai_gaps[0]
            blocker = _blocker("no_ai", item["concept"], "No-AI internalization is below A3.", item.get("assessment_evidence") or item.get("reason", ""), [item["id"]])
            action = _next_action("no_ai_reconstruction_tester", "做无 AI 重构测试", "A core concept is not yet independently reconstructable.", "Explain, distinguish, and apply it without AI hints.")
        elif trust_gaps:
            item = trust_gaps[0]
            blocker = _blocker("derivation", item["result_or_tool"], "Derivation trust is incomplete.", item.get("last_step_assessment") or "; ".join(item.get("untrusted_steps", [])), [item["id"]])
            action = _next_action("derivation_coach", "补推导信任", "Untrusted derivation steps remain.", "Reconstruct one missing step and mark whether AI hinted it.")
        elif distinction_gaps:
            item = distinction_gaps[0]
            blocker = _blocker("distinction", f"{item['concept_a']} vs {item['concept_b']}", "Distinction still needs test/retest.", item.get("last_test_result") or item.get("common_confusion", ""), [item["id"]])
            action = _next_action("example_comparison", "做概念边界测试", "Boundary evidence is missing or partial.", "Give a boundary, counterexample, and transfer example.")
        elif claim_gaps:
            item = claim_gaps[0]
            blocker = _blocker("claim", item["normalized_statement"], "Claim needs epistemic assessment or revision.", item.get("correction") or item.get("original_statement", ""), [item["id"]])
            action = _next_action("flawed_interpretation_critic", "校准 Claim 状态", "Open or wrong claims should be marked before moving on.", "State whether it is fact, inference, analogy, strategy, or wrong.")
        else:
            blocker = _blocker("none", "No active blocker", "No due assessment blocker found.", "", [])
            action = _next_action("auto_run_router", "推进下一轮", "Current learning state has no urgent repair task.", "Ask the next concrete question or press Run Next.")

        evidence = _summary_evidence(due_reviews, recurring, no_ai_gaps, trust_gaps, distinction_gaps, claim_gaps)
        return {
            "current_blocker": blocker,
            "primary_next_action": action,
            "evidence": evidence,
            "counts": {
                "open_claims": len(claim_gaps),
                "failed_reviews": len([item for item in state["review_triggers"] if item.get("status") == "failed"]),
                "recurring_misconceptions": len(recurring),
                "no_ai_below_A3": len(no_ai_gaps),
                "derivation_trust_gaps": len(trust_gaps),
                "distinctions_needing_test": len(distinction_gaps),
            },
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
        created: dict[str, list[dict[str, Any]]] = {
            "claims": [],
            "distinctions": [],
            "temporal_traces": [],
            "review_triggers": [],
            "knowledge_positions": [],
            "derivation_trust_records": [],
        }
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
        updated_claims: list[dict[str, Any]] = []
        for claim in output.get("updated_claims", []):
            claim_id = claim.get("claim_id") or claim.get("id")
            if claim_id and self.get_by_id("claims", claim_id):
                updated_claims.append(self.update_claim_epistemic_status(claim_id, claim))
        for distinction in output.get("new_distinctions", []):
            created["distinctions"].append(self.add_distinction(project_id, distinction))
        trace = output["new_temporal_trace"]
        created["temporal_traces"].append(
            self._insert("temporal_traces", {"id": new_id("trace"), "project_id": project_id, "created_at": now, **trace})
        )
        for trigger in output.get("review_triggers", []):
            created["review_triggers"].append(self.create_review_trigger(project_id, trigger))
        for position in output.get("knowledge_position_updates", []):
            created["knowledge_positions"].append(
                self._insert(
                    "knowledge_positions",
                    {
                        "id": new_id("kp"),
                        "project_id": project_id,
                        "last_assessed_at": position.get("last_assessed_at"),
                        "last_assessment_result": position.get("last_assessment_result"),
                        "assessment_evidence": position.get("assessment_evidence"),
                        "updated_at": now,
                        **position,
                    },
                )
            )
        for derivation in output.get("derivation_trust_updates", []):
            created["derivation_trust_records"].append(self.add_derivation_trust_record(project_id, derivation))
        payload = {
            "source_metadata": output.get(
                "source_metadata",
                {"source_type": "system_trace", "source_message_id": message_id, "evidence_text": ""},
            ),
            "created": created,
            "updated": {"claims": updated_claims},
            "user_originated_updates": output.get("user_originated_updates", {}),
            "ai_only_observations": output.get("ai_only_observations", {}),
            "discarded_ephemeral_judgments": output.get("discarded_ephemeral_judgments", {}),
        }
        log = self._insert(
            "state_update_logs",
            {
                "id": new_id("upd"),
                "project_id": project_id,
                "message_id": message_id,
                "update_type": "state_writer",
                "payload_json": json.dumps(payload, ensure_ascii=False),
                "status": "applied",
                "created_at": now,
            },
        )
        return {**created, "log_id": log["id"], "user_originated_updates": output.get("user_originated_updates", {})}

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
        for position in created.get("knowledge_positions", []):
            self._update("knowledge_positions", position["id"], {"review_needed": 0, "updated_at": now})
        for derivation in created.get("derivation_trust_records", []):
            self._update("derivation_trust_records", derivation["id"], {"no_ai_reconstruction_status": "reverted", "updated_at": now})
        return self._update("state_update_logs", update_id, {"status": "reverted"})


def _merge_list(left: Any, right: Any) -> list[Any]:
    result: list[Any] = []
    for value in (left or []) + (right or []):
        if value not in result:
            result.append(value)
    return result


def _max_severity(existing: str, proposed: str, count: int) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    if count >= 3:
        return "high"
    return existing if order.get(existing, 1) >= order.get(proposed, 1) else proposed


def _blocker(kind: str, title: str, reason: str, evidence: str, related_ids: list[str]) -> dict[str, Any]:
    return {"type": kind, "title": title, "reason": reason, "evidence": evidence, "related_ids": related_ids}


def _next_action(module: str, label: str, reason: str, expected_user_action: str) -> dict[str, str]:
    return {"module": module, "label": label, "reason": reason, "expected_user_action": expected_user_action}


def _summary_evidence(*groups: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for group in groups:
        for item in group[:3]:
            items.append(
                {
                    "type": _evidence_type(item),
                    "id": str(item.get("id", "")),
                    "summary": _evidence_summary(item),
                    "status": str(item.get("status") or item.get("current_level") or item.get("trust_status") or ""),
                    "why_it_matters": _evidence_reason(item),
                }
            )
    return items[:8]


def _evidence_type(item: dict[str, Any]) -> str:
    item_id = str(item.get("id", ""))
    if item_id.startswith("rev_"):
        return "review_trigger"
    if item_id.startswith("misc_"):
        return "misconception"
    if item_id.startswith("kp_"):
        return "knowledge_position"
    if item_id.startswith("der_"):
        return "derivation_trust"
    if item_id.startswith("dist_"):
        return "distinction"
    if item_id.startswith("claim_"):
        return "claim"
    return "record"


def _evidence_summary(item: dict[str, Any]) -> str:
    return str(
        item.get("target")
        or item.get("statement")
        or item.get("concept")
        or item.get("result_or_tool")
        or item.get("boundary")
        or item.get("normalized_statement")
        or item.get("id")
        or ""
    )


def _evidence_reason(item: dict[str, Any]) -> str:
    return str(
        item.get("trigger_reason")
        or item.get("next_action")
        or item.get("assessment_evidence")
        or item.get("last_step_assessment")
        or item.get("common_confusion")
        or item.get("correction")
        or ""
    )

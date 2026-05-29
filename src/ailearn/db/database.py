from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, url: str = "sqlite:///data/ai_learn_os.sqlite3") -> None:
        self.url = url

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite:///")

    @property
    def path(self) -> Path:
        if not self.is_sqlite:
            raise RuntimeError("The lightweight runtime connects only to sqlite; Postgres is supported by migrations and deployment config.")
        raw = self.url.removeprefix("sqlite:///")
        return Path(raw)

    def connect(self) -> sqlite3.Connection:
        path = self.path
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(SQLITE_SCHEMA)


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT 'general',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_settings (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL UNIQUE,
  reference_priority TEXT NOT NULL DEFAULT 'balanced',
  learning_depth TEXT NOT NULL DEFAULT 'medium',
  teaching_style TEXT NOT NULL DEFAULT 'concise',
  record_intensity TEXT NOT NULL DEFAULT 'medium',
  no_ai_strictness TEXT NOT NULL DEFAULT 'medium',
  review_frequency TEXT NOT NULL DEFAULT 'weekly',
  enabled_modules TEXT NOT NULL DEFAULT '[]',
  output_language TEXT NOT NULL DEFAULT 'zh',
  exam_research_course_mode TEXT NOT NULL DEFAULT 'general',
  default_learning_action TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_settings (
  id TEXT PRIMARY KEY,
  default_language TEXT NOT NULL DEFAULT 'zh',
  default_model_routing TEXT NOT NULL DEFAULT 'fast',
  global_response_style TEXT NOT NULL DEFAULT 'concise',
  global_record_policy TEXT NOT NULL DEFAULT 'medium',
  privacy_level TEXT NOT NULL DEFAULT 'local',
  auto_state_update INTEGER NOT NULL DEFAULT 1,
  cost_latency_preference TEXT NOT NULL DEFAULT 'balanced',
  notification_preference TEXT NOT NULL DEFAULT 'none',
  theme TEXT NOT NULL DEFAULT 'light',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS goal_stacks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  main_goal TEXT NOT NULL DEFAULT '',
  stage_goal TEXT NOT NULL DEFAULT '',
  transfer_goal TEXT NOT NULL DEFAULT '',
  external_goal TEXT NOT NULL DEFAULT '',
  conflict_goal TEXT NOT NULL DEFAULT '',
  current_focus TEXT NOT NULL DEFAULT '',
  next_action TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "references" (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  source_type TEXT NOT NULL,
  reliability_level TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT '',
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reference_chunks (
  id TEXT PRIMARY KEY,
  reference_id TEXT NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding TEXT,
  page_number INTEGER,
  section_title TEXT,
  metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  selected_mode TEXT,
  button_action TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS context_packs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  current_request TEXT NOT NULL,
  goal_context TEXT NOT NULL,
  reference_context TEXT NOT NULL,
  learning_state_context TEXT NOT NULL,
  known_confusions TEXT NOT NULL DEFAULT '[]',
  must_respect_constraints TEXT NOT NULL DEFAULT '[]',
  suggested_learning_action TEXT NOT NULL,
  ai_permission_boundary TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  original_statement TEXT NOT NULL,
  normalized_statement TEXT NOT NULL,
  related_concept TEXT NOT NULL,
  epistemic_status TEXT NOT NULL,
  confidence REAL NOT NULL,
  correction TEXT,
  source_message_id TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS distinctions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  concept_a TEXT NOT NULL,
  concept_b TEXT NOT NULL,
  boundary TEXT NOT NULL,
  common_confusion TEXT NOT NULL,
  example TEXT NOT NULL,
  test_question TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS temporal_traces (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  user_question TEXT NOT NULL,
  system_response_summary TEXT NOT NULL,
  state_change_summary TEXT NOT NULL,
  next_step TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_positions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  concept TEXT NOT NULL,
  layer TEXT NOT NULL,
  reason TEXT NOT NULL,
  target_level TEXT NOT NULL,
  current_level TEXT NOT NULL,
  review_needed INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS epistemic_marks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  epistemic_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS derivation_trust_records (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  result_or_tool TEXT NOT NULL,
  assumptions TEXT NOT NULL DEFAULT '[]',
  key_steps TEXT NOT NULL DEFAULT '[]',
  done_by_user TEXT NOT NULL DEFAULT '[]',
  hinted_by_ai TEXT NOT NULL DEFAULT '[]',
  untrusted_steps TEXT NOT NULL DEFAULT '[]',
  failure_conditions TEXT NOT NULL DEFAULT '[]',
  no_ai_reconstruction_status TEXT NOT NULL DEFAULT 'not_started',
  next_rederive_time TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_triggers (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  target TEXT NOT NULL,
  trigger_reason TEXT NOT NULL,
  review_type TEXT NOT NULL,
  scheduled_time TEXT NOT NULL,
  success_criteria TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS module_runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  message_id TEXT,
  module_name TEXT NOT NULL,
  input_summary TEXT NOT NULL,
  output_summary TEXT NOT NULL,
  model_tier TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state_update_logs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  message_id TEXT,
  update_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_questions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  question TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  statement TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_records (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  hypothesis_id TEXT,
  summary TEXT NOT NULL,
  reliability_level TEXT NOT NULL DEFAULT 'uncertain',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS competing_explanations (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  explanation TEXT NOT NULL,
  evidence_for TEXT NOT NULL DEFAULT '',
  evidence_against TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS advisor_feedback (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  feedback TEXT NOT NULL,
  action_required TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS next_experiments (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  experiment TEXT NOT NULL,
  success_criteria TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'planned',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

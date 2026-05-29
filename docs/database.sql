CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
  id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id),
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  mode text NOT NULL CHECK (mode IN ('course', 'exam', 'research', 'general')),
  status text NOT NULL CHECK (status IN ('active', 'paused', 'archived')),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS project_settings (
  id text PRIMARY KEY,
  project_id text NOT NULL UNIQUE REFERENCES projects(id),
  reference_priority text NOT NULL DEFAULT 'balanced',
  learning_depth text NOT NULL DEFAULT 'medium',
  teaching_style text NOT NULL DEFAULT 'concise',
  record_intensity text NOT NULL DEFAULT 'medium',
  no_ai_strictness text NOT NULL DEFAULT 'medium',
  review_frequency text NOT NULL DEFAULT 'weekly',
  enabled_modules jsonb NOT NULL DEFAULT '[]',
  output_language text NOT NULL DEFAULT 'zh',
  exam_research_course_mode text NOT NULL DEFAULT 'general',
  default_learning_action text,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS system_settings (
  id text PRIMARY KEY,
  default_language text NOT NULL DEFAULT 'zh',
  default_model_routing text NOT NULL DEFAULT 'fast',
  global_response_style text NOT NULL DEFAULT 'concise',
  global_record_policy text NOT NULL DEFAULT 'medium',
  privacy_level text NOT NULL DEFAULT 'local',
  auto_state_update boolean NOT NULL DEFAULT true,
  cost_latency_preference text NOT NULL DEFAULT 'balanced',
  notification_preference text NOT NULL DEFAULT 'none',
  theme text NOT NULL DEFAULT 'light',
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_stacks (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  main_goal text NOT NULL,
  stage_goal text NOT NULL DEFAULT '',
  transfer_goal text NOT NULL DEFAULT '',
  external_goal text NOT NULL DEFAULT '',
  conflict_goal text NOT NULL DEFAULT '',
  current_focus text NOT NULL DEFAULT '',
  next_action text NOT NULL DEFAULT '',
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS "references" (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  title text NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('upload', 'deep_research', 'manual', 'web', 'advisor_feedback')),
  reliability_level text NOT NULL CHECK (reliability_level IN ('high', 'medium', 'low', 'uncertain')),
  scope text NOT NULL DEFAULT '',
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_chunks (
  id text PRIMARY KEY,
  reference_id text NOT NULL REFERENCES "references"(id),
  chunk_text text NOT NULL,
  embedding vector(1536),
  page_number integer,
  section_title text,
  metadata jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content text NOT NULL,
  selected_mode text,
  button_action text,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS context_packs (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  message_id text NOT NULL REFERENCES messages(id),
  current_request text NOT NULL,
  goal_context text NOT NULL,
  reference_context text NOT NULL,
  learning_state_context text NOT NULL,
  known_confusions jsonb NOT NULL DEFAULT '[]',
  must_respect_constraints jsonb NOT NULL DEFAULT '[]',
  suggested_learning_action text NOT NULL,
  ai_permission_boundary text NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  original_statement text NOT NULL,
  normalized_statement text NOT NULL,
  related_concept text NOT NULL,
  epistemic_status text NOT NULL,
  confidence real NOT NULL,
  correction text,
  source_message_id text REFERENCES messages(id),
  status text NOT NULL CHECK (status IN ('active', 'revised', 'deprecated')),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS distinctions (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  concept_a text NOT NULL,
  concept_b text NOT NULL,
  boundary text NOT NULL,
  common_confusion text NOT NULL,
  example text NOT NULL,
  test_question text NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS temporal_traces (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  event_type text NOT NULL,
  user_question text NOT NULL,
  system_response_summary text NOT NULL,
  state_change_summary text NOT NULL,
  next_step text NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_positions (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  concept text NOT NULL,
  layer text NOT NULL CHECK (layer IN ('no_ai_internalization', 'positioning', 'index')),
  reason text NOT NULL,
  target_level text NOT NULL,
  current_level text NOT NULL,
  review_needed boolean NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS epistemic_marks (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  target_type text NOT NULL,
  target_id text NOT NULL,
  epistemic_status text NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS derivation_trust_records (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  result_or_tool text NOT NULL,
  assumptions jsonb NOT NULL DEFAULT '[]',
  key_steps jsonb NOT NULL DEFAULT '[]',
  done_by_user jsonb NOT NULL DEFAULT '[]',
  hinted_by_ai jsonb NOT NULL DEFAULT '[]',
  untrusted_steps jsonb NOT NULL DEFAULT '[]',
  failure_conditions jsonb NOT NULL DEFAULT '[]',
  no_ai_reconstruction_status text NOT NULL DEFAULT 'not_started',
  next_rederive_time timestamptz,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS review_triggers (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  target text NOT NULL,
  trigger_reason text NOT NULL,
  review_type text NOT NULL CHECK (review_type IN ('explain', 'distinguish', 'derive', 'transfer', 'error_check')),
  scheduled_time timestamptz NOT NULL,
  success_criteria text NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'completed', 'skipped')),
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS module_runs (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  message_id text REFERENCES messages(id),
  module_name text NOT NULL,
  input_summary text NOT NULL,
  output_summary text NOT NULL,
  model_tier text NOT NULL CHECK (model_tier IN ('fast', 'medium', 'strong')),
  latency_ms integer NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS state_update_logs (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  message_id text REFERENCES messages(id),
  update_type text NOT NULL,
  payload_json jsonb NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS research_questions (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  question text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  statement text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  hypothesis_id text REFERENCES hypotheses(id),
  summary text NOT NULL,
  reliability_level text NOT NULL DEFAULT 'uncertain',
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS competing_explanations (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  explanation text NOT NULL,
  evidence_for text NOT NULL DEFAULT '',
  evidence_against text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS advisor_feedback (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  feedback text NOT NULL,
  action_required text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS next_experiments (
  id text PRIMARY KEY,
  project_id text NOT NULL REFERENCES projects(id),
  experiment text NOT NULL,
  success_criteria text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'planned',
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

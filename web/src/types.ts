export type RecordItem = Record<string, unknown> & { id: string };

export interface DashboardPayload {
  status: {
    active_goal_title: string;
    references_count: number;
    unverified_claims: number;
    weak_claims: number;
    derivations_needing_trust: number;
    a_level_counts: Record<string, number>;
    tests_attention: number;
    recent_sessions: string[];
    unresolved_learning_states: string[];
  };
  next_actions: string[];
  test_suggestions: string[];
}

export interface NextActionView {
  id: string;
  title: string;
  reason: string;
  priority: number;
  action_type: "verify_claim" | "rederive" | "test_topic" | "resolve_confusion" | "review_due" | "add_reference" | "refine_goal" | "generate_prompt" | string;
  related_record_ids: string[];
  suggested_prompt_type?: string | null;
  due_date?: string | null;
}

export interface LearningItemView {
  id: string;
  source_type: string;
  title: string;
  status: string;
  position?: string;
  internalization_level?: string;
  record_intensity?: string;
  temporal_status?: string;
  due_date?: string | null;
  next_action?: string;
  updated_at: string;
  source?: RecordItem;
}

export interface DashboardView {
  active_goal: RecordItem | null;
  primary_next_action: NextActionView | null;
  secondary_next_actions: NextActionView[];
  open_loop_counts: Record<string, number>;
  top_open_loops: Record<string, unknown[]>;
  trust_gaps: RecordItem[];
  ready_for_test: LearningItemView[];
  due_reviews: string[];
  recent_activity: Array<Record<string, unknown> & { id: string }>;
  recent_references: RecordItem[];
}

export interface ApiList<T = RecordItem> {
  items: T[];
}

export interface ApiItem<T = RecordItem> {
  item: T;
}

export interface PromptResponse {
  prompt: string;
  actions?: string[];
}

export interface ValidationResponse {
  ok: boolean;
  errors: string[];
  warnings: string[];
}

export interface ProviderSummary {
  id: string;
  type: string;
  base_url: string;
  api_key_env?: string | null;
  api_key_present: boolean;
  default_model?: string | null;
  is_default: boolean;
}

export interface ProviderSettings {
  project_home: string;
  timezone: string;
  prompt_only: boolean;
  default_provider?: string | null;
  default_model?: string | null;
  context_budget: string;
  ui_host: string;
  ui_port: number;
  providers: ProviderSummary[];
}

export interface AiRunResponse {
  item: RecordItem;
  response: string;
  preview: Record<string, unknown>;
}

export type ProjectMode = "course" | "exam" | "research" | "general";
export type ProjectStatus = "active" | "paused" | "archived";
export type TeachingMode = "auto" | "explain" | "compare" | "socratic" | "derive" | "exercise" | "critic" | "review";
export type ButtonAction = "explain" | "compare" | "socratic" | "derive" | "exercise" | "correct" | "critic" | "review" | "no_ai_test";

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string;
  mode: ProjectMode;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectSettings {
  id: string;
  project_id: string;
  reference_priority: string;
  learning_depth: string;
  teaching_style: string;
  record_intensity: string;
  no_ai_strictness: string;
  review_frequency: string;
  enabled_modules: string[];
  output_language: string;
  exam_research_course_mode: string;
  default_learning_action?: string | null;
}

export interface SystemSettings {
  id: string;
  default_language: string;
  default_model_routing: string;
  global_response_style: string;
  global_record_policy: string;
  privacy_level: string;
  auto_state_update: number;
  cost_latency_preference: string;
  notification_preference: string;
  theme: string;
}

export interface ChatRequest {
  project_id: string;
  message: string;
  selected_mode: TeachingMode;
  button_action?: ButtonAction | null;
}

export interface PipelineTrace {
  steps: Array<{ agent: string; output: Record<string, unknown> }>;
  decision?: Record<string, unknown>;
  message_ids?: Record<string, string>;
  debug?: Record<string, unknown>;
}

export interface StateUpdates {
  claims?: RecordItem[];
  distinctions?: RecordItem[];
  temporal_traces?: RecordItem[];
  review_triggers?: RecordItem[];
  knowledge_positions?: RecordItem[];
  derivation_trust_records?: RecordItem[];
  log_id?: string;
}

export interface ChatResponse {
  answer: string;
  suggested_next_action: string;
  pipeline_trace: PipelineTrace;
  state_updates: StateUpdates;
}

export interface RunNextResponse {
  chosen_module: string;
  reason: string;
  answer: string;
  pipeline_trace: PipelineTrace;
  state_updates: StateUpdates;
  priority?: string;
  loop_step?: string;
  why_this_now?: string;
  expected_user_action?: string;
  will_update?: string[];
}

export interface LearningStatePayload {
  claims: RecordItem[];
  distinctions: RecordItem[];
  temporal_traces: RecordItem[];
  knowledge_positions: RecordItem[];
  derivation_trust_records: RecordItem[];
  review_triggers: RecordItem[];
  module_runs: RecordItem[];
}

export interface ReferenceEntry {
  id: string;
  project_id: string;
  title: string;
  source_type: "upload" | "deep_research" | "manual" | "web" | "advisor_feedback";
  reliability_level: "high" | "medium" | "low" | "uncertain";
  scope: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

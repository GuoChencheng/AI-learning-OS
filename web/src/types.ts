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
export type ModelPath = "strong" | "medium" | "fallback";
export type LearningUnitContextStatus = "new" | "reused" | "refreshed" | "closed" | "jumped" | "unknown";
export type RunNextDecision = "continue" | "refresh" | "jump" | "close" | "create" | "unknown";

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
  learning_unit?: Record<string, unknown>;
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

export interface ReferenceChunkUsage {
  id?: string;
  reference_id?: string;
  title?: string;
  source?: string;
  reliability_level?: "high" | "medium" | "low" | "uncertain";
  scope?: string | null;
  section_title?: string | null;
  page_number?: number | null;
  excerpt: string;
}

export interface ReferenceChunkRecord extends RecordItem {
  reference_id: string;
  chunk_text: string;
  embedding?: unknown;
  page_number?: number | null;
  section_title?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ActiveLearningUnitView {
  id: string;
  mode: string;
  topic?: string;
  status?: LearningUnit["status"];
  turnCount: number;
  contextStatus: LearningUnitContextStatus;
  action?: string;
  reason?: string;
}

export interface MessageMetadata {
  modelPath?: ModelPath;
  activeLearningUnit?: ActiveLearningUnitView | null;
  referenceChunks?: ReferenceChunkUsage[];
}

export interface RunNextDecisionState {
  decision: RunNextDecision;
  reason: string;
  priority?: string;
  loopStep?: string;
  expectedUserAction?: string;
}

export interface ChatResponse {
  answer: string;
  suggested_next_action: string;
  pipeline_trace: PipelineTrace;
  state_updates: StateUpdates;
  active_learning_unit?: LearningUnit | null;
  model_path?: ModelPath;
  reference_chunks?: ReferenceChunkUsage[];
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
  active_learning_unit?: LearningUnit | null;
  decision?: RunNextDecision;
  model_path?: ModelPath;
  reference_chunks?: ReferenceChunkUsage[];
}

export interface LearningUnit {
  id: string;
  project_id: string;
  status: "active" | "closed" | "abandoned";
  method: string;
  topic: string;
  start_message_id?: string | null;
  last_message_id?: string | null;
  context_snapshot_json: Record<string, unknown>;
  unit_summary: string;
  turn_count: number;
  close_reason?: string | null;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
}

export interface LearningStatePayload {
  claims: RecordItem[];
  distinctions: RecordItem[];
  temporal_traces: RecordItem[];
  knowledge_positions: RecordItem[];
  derivation_trust_records: RecordItem[];
  review_triggers: RecordItem[];
  module_runs: RecordItem[];
  learning_units?: LearningUnit[];
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

export interface SeedProjectResponse {
  status: "ok";
  project_id: string;
  project: Project;
}

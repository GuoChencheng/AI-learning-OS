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

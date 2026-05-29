import type {
  ApiItem,
  ApiList,
  AiRunResponse,
  ActiveLearningUnitView,
  ChatRequest,
  ChatResponse,
  LearningUnit,
  LearningStatePayload,
  LearningUnitContextStatus,
  MessageMetadata,
  ModelPath,
  Project,
  ProjectSettings,
  ProviderSettings,
  ReferenceChunkRecord,
  ReferenceEntry,
  ReferenceChunkUsage,
  RunNextDecision,
  RunNextDecisionState,
  RunNextResponse,
  SeedProjectResponse,
  SystemSettings
} from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
  } catch (err) {
    throw new Error(`API server is not reachable. Start the backend on 127.0.0.1:8765, then retry. (${err instanceof Error ? err.message : "network error"})`);
  }
  const raw = await response.text();
  const data = parseJsonResponse(raw, path);
  if (!response.ok) {
    const message = typeof data === "object" && data && "error" in data ? String(data.error) : `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return data as T;
}

function parseJsonResponse(raw: string, path: string): unknown {
  if (!raw.trim()) {
    throw new Error(`API returned an empty response for ${path}. The backend may be stopped or still running an old server build.`);
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`API returned non-JSON for ${path}. Check that the backend server is running the current AI Learn OS API.`);
  }
}

export const api = {
  chat: (body: ChatRequest) => request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(body) }),
  runNext: (project_id: string) => request<RunNextResponse>("/api/run-next", { method: "POST", body: JSON.stringify({ project_id }) }),
  projects: () => request<ApiList<Project>>("/api/projects"),
  createProject: (body: Partial<Project> & { name: string }) => request<Project>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
  seedCftProject: () => request<SeedProjectResponse>("/api/projects/seed/cft", { method: "POST", body: JSON.stringify({}) }),
  project: (id: string) => request<Project>(`/api/projects/${id}`),
  updateProject: (id: string, body: Partial<Project>) => request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  projectSettings: (id: string) => request<ProjectSettings>(`/api/projects/${id}/settings`),
  updateProjectSettings: (id: string, body: Partial<ProjectSettings>) =>
    request<ProjectSettings>(`/api/projects/${id}/settings`, { method: "PATCH", body: JSON.stringify(body) }),
  systemSettings: () => request<SystemSettings>("/api/system-settings"),
  updateSystemSettings: (body: Partial<SystemSettings>) =>
    request<SystemSettings>("/api/system-settings", { method: "PATCH", body: JSON.stringify(body) }),
  state: (id: string) => request<LearningStatePayload>(`/api/projects/${id}/state`),
  activeLearningUnit: (projectId: string) => request<ApiItem<LearningUnit | null>>(`/api/projects/${projectId}/learning-units/active`),
  learningUnits: (projectId: string) => request<ApiList<LearningUnit>>(`/api/projects/${projectId}/learning-units`),
  closeLearningUnit: (projectId: string, unitId: string) =>
    request<LearningUnit>(`/api/projects/${projectId}/learning-units/${unitId}/close`, { method: "POST", body: JSON.stringify({}) }),
  refreshLearningUnitContext: (projectId: string, unitId: string) =>
    request<LearningUnit>(`/api/projects/${projectId}/learning-units/${unitId}/refresh-context`, { method: "POST", body: JSON.stringify({}) }),
  claims: (id: string) => request<ApiList>(`/api/projects/${id}/claims`),
  distinctions: (id: string) => request<ApiList>(`/api/projects/${id}/distinctions`),
  reviewTriggers: (id: string) => request<ApiList>(`/api/projects/${id}/review-triggers`),
  knowledgePositions: (id: string) => request<ApiList>(`/api/projects/${id}/knowledge-positions`),
  references: (id: string) => request<ApiList<ReferenceEntry>>(`/api/projects/${id}/references`),
  createReference: (projectId: string, body: Record<string, unknown>) =>
    request<ReferenceEntry>(`/api/projects/${projectId}/references`, { method: "POST", body: JSON.stringify(body) }),
  uploadReference: (projectId: string, body: Record<string, unknown>) =>
    request<ReferenceEntry>(`/api/projects/${projectId}/references/upload`, { method: "POST", body: JSON.stringify(body) }),
  referenceChunks: (id: string) => request<ApiList<ReferenceChunkRecord>>(`/api/references/${id}/chunks`),
  revertStateUpdate: (id: string) => request<Record<string, unknown>>(`/api/state-updates/${id}/revert`, { method: "POST", body: JSON.stringify({}) }),
  providerSettings: () => request<ProviderSettings>("/api/settings/providers"),
  aiRunText: (body: Record<string, unknown>) =>
    request<AiRunResponse>("/api/ai/run-text", { method: "POST", body: JSON.stringify(body) }),
  list: <T = Record<string, unknown>>(resource: string, query = "") => request<ApiList<T>>(`/api/${resource}${query}`),
  show: <T = Record<string, unknown>>(resource: string, id: string) => request<ApiItem<T>>(`/api/${resource}/${id}`)
};

export function extractMessageMetadata(response: ChatResponse | RunNextResponse): MessageMetadata {
  const learningUnitTrace = getRecord(response.pipeline_trace.learning_unit);
  return {
    modelPath: normalizeModelPath(response.model_path),
    activeLearningUnit: buildActiveLearningUnitView(response.active_learning_unit, learningUnitTrace),
    referenceChunks: extractReferenceChunks(response)
  };
}

export function extractRunNextDecision(response: RunNextResponse): RunNextDecisionState {
  const learningUnitTrace = getRecord(response.pipeline_trace.learning_unit);
  const decision = normalizeRunNextDecision(response.decision) || decisionFromLearningUnitAction(asString(learningUnitTrace.action));
  return {
    decision,
    reason: response.why_this_now || asString(learningUnitTrace.reason) || response.reason,
    priority: response.priority,
    loopStep: response.loop_step,
    expectedUserAction: response.expected_user_action
  };
}

function buildActiveLearningUnitView(unit: LearningUnit | null | undefined, trace: Record<string, unknown>): ActiveLearningUnitView | null {
  const id = unit?.id || asString(trace.id);
  if (!id) return null;
  const action = asString(trace.action);
  return {
    id,
    mode: unit?.method || asString(trace.method) || "auto",
    topic: unit?.topic || asString(trace.topic) || undefined,
    status: unit?.status,
    turnCount: Number(unit?.turn_count ?? trace.turn_count ?? 0),
    contextStatus: contextStatusFromAction(action, Boolean(trace.should_run_full_context_extraction)),
    action: action || undefined,
    reason: asString(trace.reason) || undefined
  };
}

function extractReferenceChunks(response: ChatResponse | RunNextResponse): ReferenceChunkUsage[] {
  const direct = normalizeReferenceChunks(response.reference_chunks);
  if (direct.length > 0) return direct;

  const fromTrace = response.pipeline_trace.steps.flatMap((step) => {
    const output = getRecord(step.output);
    return normalizeReferenceChunks(output.relevant_reference_chunks);
  });
  if (fromTrace.length > 0) return dedupeChunks(fromTrace);

  const snapshot = getRecord(response.active_learning_unit?.context_snapshot_json);
  const extractor = getRecord(snapshot.context_extractor);
  return dedupeChunks(normalizeReferenceChunks(extractor.relevant_reference_chunks));
}

function normalizeReferenceChunks(value: unknown): ReferenceChunkUsage[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const record = getRecord(item);
    const excerpt = asString(record.excerpt) || asString(record.chunk_text) || asString(record.text);
    if (!excerpt) return [];
    return [{
      id: asString(record.id) || undefined,
      reference_id: asString(record.reference_id) || undefined,
      title: asString(record.title) || asString(record.source) || undefined,
      source: asString(record.source) || asString(record.title) || undefined,
      reliability_level: normalizeReliability(record.reliability_level),
      scope: asNullableString(record.scope),
      section_title: asNullableString(record.section_title),
      page_number: typeof record.page_number === "number" ? record.page_number : null,
      excerpt
    }];
  });
}

function dedupeChunks(chunks: ReferenceChunkUsage[]): ReferenceChunkUsage[] {
  const seen = new Set<string>();
  return chunks.filter((chunk) => {
    const key = chunk.id || `${chunk.reference_id || chunk.title || "chunk"}:${chunk.excerpt.slice(0, 80)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function contextStatusFromAction(action: string, fullExtraction: boolean): LearningUnitContextStatus {
  if (action === "continue_active_unit" || (!fullExtraction && action === "reuse_active_unit")) return "reused";
  if (action === "reuse_active_unit") return "reused";
  if (action === "refresh_unit_context" || action === "refresh_active_unit") return "refreshed";
  if (action === "close_active_unit" || action === "no_unit") return "closed";
  if (action === "jump_to_global_priority") return "jumped";
  if (action === "create_new_unit" || action === "close_and_create_new") return "new";
  return fullExtraction ? "new" : "unknown";
}

function decisionFromLearningUnitAction(action: string): RunNextDecision {
  if (action === "continue_active_unit") return "continue";
  if (action === "refresh_active_unit" || action === "refresh_unit_context") return "refresh";
  if (action === "jump_to_global_priority") return "jump";
  if (action === "close_active_unit" || action === "no_unit") return "close";
  if (action === "create_new_unit" || action === "close_and_create_new") return "create";
  return "unknown";
}

function normalizeRunNextDecision(value: unknown): RunNextDecision | undefined {
  return value === "continue" || value === "refresh" || value === "jump" || value === "close" || value === "create" || value === "unknown"
    ? value
    : undefined;
}

function normalizeModelPath(value: unknown): ModelPath | undefined {
  return value === "strong" || value === "medium" || value === "fallback" ? value : undefined;
}

function normalizeReliability(value: unknown): ReferenceChunkUsage["reliability_level"] | undefined {
  return value === "high" || value === "medium" || value === "low" || value === "uncertain" ? value : undefined;
}

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

import type {
  ApiItem,
  ApiList,
  AiRunResponse,
  ChatRequest,
  ChatResponse,
  LearningStatePayload,
  Project,
  ProjectSettings,
  ProviderSettings,
  ReferenceEntry,
  RunNextResponse,
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
  project: (id: string) => request<Project>(`/api/projects/${id}`),
  updateProject: (id: string, body: Partial<Project>) => request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  projectSettings: (id: string) => request<ProjectSettings>(`/api/projects/${id}/settings`),
  updateProjectSettings: (id: string, body: Partial<ProjectSettings>) =>
    request<ProjectSettings>(`/api/projects/${id}/settings`, { method: "PATCH", body: JSON.stringify(body) }),
  systemSettings: () => request<SystemSettings>("/api/system-settings"),
  updateSystemSettings: (body: Partial<SystemSettings>) =>
    request<SystemSettings>("/api/system-settings", { method: "PATCH", body: JSON.stringify(body) }),
  state: (id: string) => request<LearningStatePayload>(`/api/projects/${id}/state`),
  claims: (id: string) => request<ApiList>(`/api/projects/${id}/claims`),
  distinctions: (id: string) => request<ApiList>(`/api/projects/${id}/distinctions`),
  reviewTriggers: (id: string) => request<ApiList>(`/api/projects/${id}/review-triggers`),
  knowledgePositions: (id: string) => request<ApiList>(`/api/projects/${id}/knowledge-positions`),
  references: (id: string) => request<ApiList<ReferenceEntry>>(`/api/projects/${id}/references`),
  createReference: (projectId: string, body: Record<string, unknown>) =>
    request<ReferenceEntry>(`/api/projects/${projectId}/references`, { method: "POST", body: JSON.stringify(body) }),
  uploadReference: (projectId: string, body: Record<string, unknown>) =>
    request<ReferenceEntry>(`/api/projects/${projectId}/references/upload`, { method: "POST", body: JSON.stringify(body) }),
  referenceChunks: (id: string) => request<ApiList>(`/api/references/${id}/chunks`),
  revertStateUpdate: (id: string) => request<Record<string, unknown>>(`/api/state-updates/${id}/revert`, { method: "POST", body: JSON.stringify({}) }),
  providerSettings: () => request<ProviderSettings>("/api/settings/providers"),
  aiRunText: (body: Record<string, unknown>) =>
    request<AiRunResponse>("/api/ai/run-text", { method: "POST", body: JSON.stringify(body) }),
  list: <T = Record<string, unknown>>(resource: string, query = "") => request<ApiList<T>>(`/api/${resource}${query}`),
  show: <T = Record<string, unknown>>(resource: string, id: string) => request<ApiItem<T>>(`/api/${resource}/${id}`)
};

import type { AiRunResponse, ApiItem, ApiList, DashboardPayload, DashboardView, LearningItemView, PromptResponse, ProviderSettings, RecordItem, ValidationResponse } from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data as T;
}

export const api = {
  dashboard: () => request<DashboardPayload>("/api/dashboard"),
  dashboardView: () => request<DashboardView>("/api/dashboard-view"),
  learningItems: () => request<ApiList<LearningItemView>>("/api/learning-items"),
  validate: () => request<ValidationResponse>("/api/validate"),
  list: <T = RecordItem>(resource: string, query = "") => request<ApiList<T>>(`/api/${resource}${query}`),
  show: <T = RecordItem>(resource: string, id: string) => request<ApiItem<T>>(`/api/${resource}/${id}`),
  create: <T = RecordItem>(resource: string, body: Record<string, unknown>) =>
    request<ApiItem<T>>(`/api/${resource}`, { method: "POST", body: JSON.stringify(body) }),
  update: <T = RecordItem>(resource: string, id: string, body: Record<string, unknown>) =>
    request<ApiItem<T>>(`/api/${resource}/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  activeGoal: () => request<ApiItem>("/api/goals/active"),
  setActiveGoal: (goal_id: string) =>
    request<ApiItem>("/api/goals/active", { method: "POST", body: JSON.stringify({ goal_id }) }),
  sessions: () => request<ApiList>("/api/sessions"),
  createSession: (body: Record<string, unknown>) =>
    request<ApiItem>("/api/sessions", { method: "POST", body: JSON.stringify(body) }),
  researchImports: () => request<ApiList>("/api/research-imports"),
  reviews: () => request<ApiList<{ id: string; path: string; name: string; markdown: string }>>("/api/reviews"),
  events: () => request<ApiList>("/api/events"),
  indexMarkdown: (kind: "active-goal" | "open-loops" | "recent") => request<{ markdown: string }>(`/api/indexes/${kind}`),
  indexes: () => request<{ summary: string }>("/api/indexes"),
  contextPolicy: () => request<{ policy: string }>("/api/context/policy"),
  providerSettings: () => request<ProviderSettings>("/api/settings/providers"),
  providerTest: (providerId: string) =>
    request<{ ok: boolean; message: string }>(`/api/settings/providers/test/${providerId}`, { method: "POST", body: JSON.stringify({}) }),
  aiRuns: () => request<ApiList>("/api/ai/runs"),
  aiRunText: (body: Record<string, unknown>) =>
    request<AiRunResponse>("/api/ai/run-text", { method: "POST", body: JSON.stringify(body) }),
  generateReview: () =>
    request<{ path: string; markdown: string }>("/api/reviews/weekly", { method: "POST", body: JSON.stringify({}) }),
  prompt: (kind: string, body: Record<string, unknown>) =>
    request<PromptResponse>(`/api/prompts/${kind}`, { method: "POST", body: JSON.stringify(body) }),
  methodSuggest: (state: string) =>
    request<{ state: string; actions: string[]; rationale: string }>("/api/method/suggest", {
      method: "POST",
      body: JSON.stringify({ state })
    }),
  testSuggestions: () => request<ApiList<string>>("/api/tests/suggest")
};

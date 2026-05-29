import { api } from "./api";
import type { ChatResponse, Project, RunNextResponse } from "./types";

async function apiClientSmoke(project: Project): Promise<[ChatResponse, RunNextResponse]> {
  const chat = await api.chat({
    project_id: project.id,
    message: "What should I test next?",
    selected_mode: "auto",
    button_action: null
  });
  const next = await api.runNext(project.id);
  return [chat, next];
}

void apiClientSmoke;

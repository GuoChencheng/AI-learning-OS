import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronRight,
  GitCompare,
  GraduationCap,
  History,
  MessageSquareText,
  PenLine,
  Plus,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  X
} from "lucide-react";
import { api } from "./api";
import { MarkdownRenderer } from "./components/MarkdownRenderer";
import type {
  ButtonAction,
  ChatResponse,
  LearningStatePayload,
  Project,
  ProjectSettings,
  ReferenceEntry,
  RunNextResponse,
  SystemSettings,
  TeachingMode
} from "./types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  mode?: string;
  updateHint?: string;
  updateLogId?: string;
  reverted?: boolean;
};

type DrawerTab = "projects" | "project-settings" | "system-settings" | "learning-state";

const actionButtons: Array<{ action: ButtonAction; mode: TeachingMode; label: string; icon: typeof Sparkles }> = [
  { action: "explain", mode: "explain", label: "解释", icon: Sparkles },
  { action: "compare", mode: "compare", label: "比较", icon: GitCompare },
  { action: "socratic", mode: "socratic", label: "追问", icon: MessageSquareText },
  { action: "derive", mode: "derive", label: "推导", icon: PenLine },
  { action: "exercise", mode: "exercise", label: "出题", icon: GraduationCap },
  { action: "correct", mode: "exercise", label: "改错", icon: CheckCircle2 },
  { action: "critic", mode: "critic", label: "审查", icon: ShieldCheck },
  { action: "review", mode: "review", label: "回看", icon: History },
  { action: "no_ai_test", mode: "review", label: "无 AI 测试", icon: Brain }
];

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState("");
  const [projectSettings, setProjectSettings] = useState<ProjectSettings | null>(null);
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null);
  const [learningState, setLearningState] = useState<LearningStatePayload | null>(null);
  const [references, setReferences] = useState<ReferenceEntry[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "选择或创建一个学习项目，然后直接提问。系统会在后台完成定位、路由、回答和学习状态写回。",
      updateHint: "等待项目"
    }
  ]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>("projects");
  const [input, setInput] = useState("");
  const [activeAction, setActiveAction] = useState<ButtonAction | null>(null);
  const [selectedMode, setSelectedMode] = useState<TeachingMode>("auto");
  const [actionMenuOpen, setActionMenuOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [referenceTitle, setReferenceTitle] = useState("");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const currentProject = useMemo(
    () => projects.find((project) => project.id === currentProjectId) || projects[0] || null,
    [projects, currentProjectId]
  );

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!currentProject?.id) return;
    void refreshProjectSurfaces(currentProject.id);
  }, [currentProject?.id]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function bootstrap() {
    try {
      const list = await api.projects();
      if (list.items.length > 0) {
        setProjects(list.items);
        setCurrentProjectId(list.items[0].id);
      } else {
        const created = await api.createProject({ name: "General Learning", description: "Default AI Learn OS project" });
        setProjects([created]);
        setCurrentProjectId(created.id);
      }
      setSystemSettings(await api.systemSettings());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects.");
    }
  }

  async function refreshProjectSurfaces(projectId: string) {
    const [settings, state, refs] = await Promise.all([
      api.projectSettings(projectId),
      api.state(projectId),
      api.references(projectId)
    ]);
    setProjectSettings(settings);
    setLearningState(state);
    setReferences(refs.items);
  }

  async function sendMessage() {
    if (!currentProject || !input.trim() || busy) return;
    const content = input.trim();
    setInput("");
    setBusy(true);
    setError("");
    const action = activeAction;
    const mode = action ? actionButtons.find((item) => item.action === action)?.mode || selectedMode : selectedMode;
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: "user", content, mode: action || mode }]);
    try {
      const response = await api.chat({
        project_id: currentProject.id,
        message: content,
        selected_mode: mode,
        button_action: action
      });
      appendAssistant(response);
      await refreshProjectSurfaces(currentProject.id);
      setActiveAction(null);
      setSelectedMode("auto");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runNext() {
    if (!currentProject || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.runNext(currentProject.id);
      appendRunNext(response);
      await refreshProjectSurfaces(currentProject.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run next failed.");
    } finally {
      setBusy(false);
    }
  }

  function appendAssistant(response: ChatResponse) {
    setMessages((items) => [
      ...items,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        updateHint: summarizeUpdates(response),
        updateLogId: response.state_updates.log_id
      }
    ]);
  }

  function appendRunNext(response: RunNextResponse) {
    setMessages((items) => [
      ...items,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        mode: response.chosen_module,
        updateHint: summarizeRunNext(response),
        updateLogId: response.state_updates.log_id
      }
    ]);
  }

  async function createProject() {
    if (!newProjectName.trim()) return;
    const created = await api.createProject({ name: newProjectName.trim(), description: "Created from the web UI" });
    setProjects((items) => [created, ...items]);
    setCurrentProjectId(created.id);
    setNewProjectName("");
  }

  async function updateProjectSettings(patch: Partial<ProjectSettings>) {
    if (!currentProject) return;
    const updated = await api.updateProjectSettings(currentProject.id, patch);
    setProjectSettings(updated);
  }

  async function updateProject(patch: Partial<Project>) {
    if (!currentProject) return;
    const updated = await api.updateProject(currentProject.id, patch);
    setProjects((items) => items.map((item) => item.id === updated.id ? updated : item));
    setCurrentProjectId(updated.id);
  }

  async function updateSystemSettings(patch: Partial<SystemSettings>) {
    setSystemSettings(await api.updateSystemSettings(patch));
  }

  async function revertMessageUpdate(messageId: string, logId: string) {
    if (!currentProject || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.revertStateUpdate(logId);
      setMessages((items) => items.map((item) => item.id === messageId ? { ...item, reverted: true, updateHint: "已撤销本轮状态写回" } : item));
      await refreshProjectSurfaces(currentProject.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revert failed.");
    } finally {
      setBusy(false);
    }
  }

  async function addReference() {
    if (!currentProject || !referenceTitle.trim() || !referenceText.trim()) return;
    await api.createReference(currentProject.id, {
      title: referenceTitle.trim(),
      source_type: "manual",
      reliability_level: "uncertain",
      scope: "pasted reference",
      text: referenceText
    });
    setReferenceTitle("");
    setReferenceText("");
    await refreshProjectSurfaces(currentProject.id);
  }

  async function handleFile(file: File) {
    if (!currentProject) return;
    if (file.name.toLowerCase().endsWith(".pdf")) {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
      });
      await api.uploadReference(currentProject.id, {
        title: file.name,
        filename: file.name,
        source_type: "upload",
        reliability_level: "uncertain",
        scope: file.type || "uploaded pdf",
        content_base64: btoa(binary)
      });
    } else {
      const text = await file.text();
      await api.uploadReference(currentProject.id, {
        title: file.name,
        filename: file.name,
        source_type: "upload",
        reliability_level: "uncertain",
        scope: file.type || "uploaded file",
        text
      });
    }
    await refreshProjectSurfaces(currentProject.id);
  }

  const stateLabel = useMemo(() => {
    const position = learningState?.knowledge_positions[0];
    return position?.current_level ? `${String(position.current_level)}: Internalizing` : "A1: Internalizing";
  }, [learningState]);

  const hudGoal = learningState?.temporal_traces[0]?.next_step
    ? String(learningState.temporal_traces[0].next_step)
    : "Ask normally; the OS chooses the next learning action.";
  const hudClaim = learningState?.claims[0]?.normalized_statement
    ? String(learningState.claims[0].normalized_statement)
    : "No durable claim yet.";

  return (
    <div className="learn-shell">
      <main className="chat-surface">
        <TopBar
          projects={projects}
          currentProject={currentProject}
          onProjectChange={setCurrentProjectId}
          stateLabel={stateLabel}
          goal={hudGoal}
          claim={hudClaim}
          onToggleDrawer={() => setDrawerOpen((value) => !value)}
        />
        <section className="message-list" aria-label="Conversation">
          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} busy={busy} onRevert={revertMessageUpdate} />
          ))}
          <div ref={messageEndRef} />
        </section>
        {error && <div className="error-strip">{error}</div>}
        <Composer
          value={input}
          busy={busy}
          activeAction={activeAction}
          actionMenuOpen={actionMenuOpen}
          onChange={setInput}
          onSend={sendMessage}
          onRun={runNext}
          onToggleActions={() => setActionMenuOpen((value) => !value)}
          onSelectAction={(action, mode) => {
            setActiveAction(action);
            setSelectedMode(mode);
            setActionMenuOpen(false);
          }}
        />
      </main>
      <RightDrawer
        open={drawerOpen}
        tab={drawerTab}
        onTabChange={setDrawerTab}
        onClose={() => setDrawerOpen(false)}
        projects={projects}
        currentProject={currentProject}
        projectSettings={projectSettings}
        systemSettings={systemSettings}
        learningState={learningState}
        references={references}
        newProjectName={newProjectName}
        referenceTitle={referenceTitle}
        referenceText={referenceText}
        onNewProjectName={setNewProjectName}
        onCreateProject={createProject}
        onSelectProject={setCurrentProjectId}
        onProject={updateProject}
        onProjectSettings={updateProjectSettings}
        onSystemSettings={updateSystemSettings}
        onReferenceTitle={setReferenceTitle}
        onReferenceText={setReferenceText}
        onAddReference={addReference}
        onFile={handleFile}
      />
    </div>
  );
}

function TopBar({
  projects,
  currentProject,
  onProjectChange,
  stateLabel,
  goal,
  claim,
  onToggleDrawer
}: {
  projects: Project[];
  currentProject: Project | null;
  onProjectChange: (id: string) => void;
  stateLabel: string;
  goal: string;
  claim: string;
  onToggleDrawer: () => void;
}) {
  return (
    <header className="top-bar">
      <label className="hud-breadcrumb">
        <span>✦ AI Learn OS</span>
        <span className="hud-slash">/</span>
        <select value={currentProject?.id || ""} onChange={(event) => onProjectChange(event.target.value)}>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
      </label>
      <div className="hud-state" title={`${goal} · ${claim}`}>
        <span>{stateLabel}</span>
        <small>{goal} · {claim}</small>
      </div>
      <button className="hud-settings" onClick={onToggleDrawer} title="设置与学习状态">
        <Settings size={18} />
      </button>
    </header>
  );
}

function ChatBubble({
  message,
  busy,
  onRevert
}: {
  message: ChatMessage;
  busy: boolean;
  onRevert: (messageId: string, logId: string) => void;
}) {
  const tag = extractEpistemicTag(message.content);
  return (
    <article className={`message-row ${message.role}`}>
      {message.role !== "user" && (
        <div className="ai-avatar">
          <Brain size={14} />
        </div>
      )}
      <div className="message-content">
        <div className="message-meta">
          {message.role === "user" ? "You" : "AI Learn OS"}{message.mode ? ` · ${message.mode}` : ""}
          {tag && <span className="epistemic-tag">{tag.label}</span>}
        </div>
        <div className="message-bubble">
          <MarkdownRenderer markdown={tag ? tag.body : message.content} />
        </div>
        {message.updateHint && (
          <div className="state-hint">
            <span>{message.updateHint}</span>
            {message.updateLogId && !message.reverted && (
              <button className="link-control" onClick={() => onRevert(message.id, message.updateLogId!)} disabled={busy}>
                撤销写回
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

function Composer({
  value,
  activeAction,
  actionMenuOpen,
  busy,
  onChange,
  onSend,
  onRun,
  onToggleActions,
  onSelectAction
}: {
  value: string;
  activeAction: ButtonAction | null;
  actionMenuOpen: boolean;
  busy: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onRun: () => void;
  onToggleActions: () => void;
  onSelectAction: (action: ButtonAction, mode: TeachingMode) => void;
}) {
  const hasInput = Boolean(value.trim());
  return (
    <footer className="composer-shell">
      <div className="mode-line">
        <span className={activeAction ? "method-chip manual" : "method-chip"}>
          {activeAction ? `手动：${labelForAction(activeAction)}` : "自动选择方法"}
        </span>
      </div>
      <div className="composer">
        <div className="action-popover-anchor">
          <button className="plus-control" onClick={onToggleActions} disabled={busy} title="教学方法">
            <Plus size={19} />
          </button>
          {actionMenuOpen && (
            <div className="action-popover">
              {actionButtons.filter((item) => item.action !== "correct" && item.action !== "no_ai_test").map(({ action, mode, label, icon: Icon }) => (
                <button
                  key={action}
                  className={activeAction === action ? "action-option active" : "action-option"}
                  onClick={() => onSelectAction(action, mode)}
                >
                  <Icon size={15} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <textarea
          value={value}
          placeholder={activeAction ? `${labelForAction(activeAction)}模式已选择……` : "Ask a question, or let the OS decide..."}
          rows={1}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (hasInput) void onSend();
            }
          }}
        />
        <div className="composer-actions">
          <button
            className={hasInput ? "magic-action send" : "magic-action run"}
            onClick={hasInput ? onSend : onRun}
            disabled={busy}
            title={hasInput ? "发送" : "Run Next"}
          >
            {hasInput ? <Send size={18} /> : <><Sparkles size={16} /><span>Run Next</span></>}
          </button>
        </div>
      </div>
    </footer>
  );
}

function labelForAction(action: ButtonAction) {
  return actionButtons.find((item) => item.action === action)?.label || action;
}

function extractEpistemicTag(content: string) {
  const match = content.match(/^\[(Hypothesis|Fact|Error|Claim|Review)\]\s*(.*)$/i);
  if (!match) return null;
  return { label: match[1], body: match[2] };
}

function RightDrawer(props: {
  open: boolean;
  tab: DrawerTab;
  onTabChange: (tab: DrawerTab) => void;
  onClose: () => void;
  projects: Project[];
  currentProject: Project | null;
  projectSettings: ProjectSettings | null;
  systemSettings: SystemSettings | null;
  learningState: LearningStatePayload | null;
  references: ReferenceEntry[];
  newProjectName: string;
  referenceTitle: string;
  referenceText: string;
  onNewProjectName: (value: string) => void;
  onCreateProject: () => void;
  onSelectProject: (id: string) => void;
  onProject: (patch: Partial<Project>) => void;
  onProjectSettings: (patch: Partial<ProjectSettings>) => void;
  onSystemSettings: (patch: Partial<SystemSettings>) => void;
  onReferenceTitle: (value: string) => void;
  onReferenceText: (value: string) => void;
  onAddReference: () => void;
  onFile: (file: File) => void;
}) {
  return (
    <aside className={props.open ? "right-drawer open" : "right-drawer"} aria-hidden={!props.open}>
      <div className="drawer-header">
        <div>
          <strong>设置 / 状态</strong>
          <span>{props.currentProject?.name || "No project"}</span>
        </div>
        <button className="icon-control" onClick={props.onClose} title="关闭">
          <X size={18} />
        </button>
      </div>
      <nav className="drawer-tabs">
        <TabButton id="projects" active={props.tab} onClick={props.onTabChange} label="Projects" />
        <TabButton id="project-settings" active={props.tab} onClick={props.onTabChange} label="Project Settings" />
        <TabButton id="system-settings" active={props.tab} onClick={props.onTabChange} label="System Settings" />
        <TabButton id="learning-state" active={props.tab} onClick={props.onTabChange} label="Learning State" />
      </nav>
      <div className="drawer-body">
        {props.tab === "projects" && <ProjectsTab {...props} />}
        {props.tab === "project-settings" && (
          <ProjectSettingsTab project={props.currentProject} settings={props.projectSettings} onProject={props.onProject} onPatch={props.onProjectSettings} />
        )}
        {props.tab === "system-settings" && <SystemSettingsTab settings={props.systemSettings} onPatch={props.onSystemSettings} />}
        {props.tab === "learning-state" && <LearningStateTab {...props} />}
      </div>
    </aside>
  );
}

function TabButton({ id, active, onClick, label }: { id: DrawerTab; active: DrawerTab; onClick: (tab: DrawerTab) => void; label: string }) {
  return <button className={active === id ? "active" : ""} onClick={() => onClick(id)}>{label}</button>;
}

function ProjectsTab(props: {
  projects: Project[];
  currentProject: Project | null;
  learningState?: LearningStatePayload | null;
  newProjectName: string;
  onNewProjectName: (value: string) => void;
  onCreateProject: () => void;
  onSelectProject: (id: string) => void;
}) {
  const latestTrace = props.learningState?.temporal_traces[0];
  return (
    <section className="drawer-section">
      <div className="inline-form">
        <input value={props.newProjectName} placeholder="New project name" onChange={(event) => props.onNewProjectName(event.target.value)} />
        <button className="icon-control strong" onClick={props.onCreateProject} title="创建项目"><Plus size={16} /></button>
      </div>
      <div className="project-list">
        {props.projects.map((project) => (
          <button
            key={project.id}
            className={props.currentProject?.id === project.id ? "project-card active" : "project-card"}
            onClick={() => props.onSelectProject(project.id)}
          >
            <span>
              <strong>{project.name}</strong>
              <small>{props.currentProject?.id === project.id ? String(latestTrace?.next_step || project.description || "Ask a question or run next.") : project.description || "Select to load state."}</small>
              <small>{props.currentProject?.id === project.id && latestTrace?.created_at ? `最近学习：${formatShortTime(String(latestTrace.created_at))}` : project.status}</small>
            </span>
            <ChevronRight size={16} />
          </button>
        ))}
      </div>
    </section>
  );
}

function ProjectSettingsTab({
  project,
  settings,
  onProject,
  onPatch
}: {
  project: Project | null;
  settings: ProjectSettings | null;
  onProject: (patch: Partial<Project>) => void;
  onPatch: (patch: Partial<ProjectSettings>) => void;
}) {
  if (!settings) return <EmptyState text="Project settings will appear after selecting a project." />;
  return (
    <section className="settings-grid">
      <TextField label="Project Name" value={project?.name || ""} onChange={(value) => onProject({ name: value })} />
      <SelectField label="Project Status" value={project?.status || "active"} options={["active", "paused", "archived"]} onChange={(value) => onProject({ status: value as Project["status"] })} />
      <SelectField label="Project Mode" value={project?.mode || "general"} options={["course", "exam", "research", "general"]} onChange={(value) => onProject({ mode: value as Project["mode"] })} />
      <SelectField label="Reference Priority" value={settings.reference_priority} options={["balanced", "latest", "reliable", "manual_first"]} onChange={(value) => onPatch({ reference_priority: value })} />
      <SelectField label="Learning Depth" value={settings.learning_depth} options={["light", "medium", "deep"]} onChange={(value) => onPatch({ learning_depth: value })} />
      <SelectField label="Teaching Style" value={settings.teaching_style} options={["concise", "socratic", "exam", "research"]} onChange={(value) => onPatch({ teaching_style: value })} />
      <SelectField label="Record Intensity" value={settings.record_intensity} options={["light", "medium", "heavy"]} onChange={(value) => onPatch({ record_intensity: value })} />
      <SelectField label="No-AI Strictness" value={settings.no_ai_strictness} options={["low", "medium", "high"]} onChange={(value) => onPatch({ no_ai_strictness: value })} />
      <SelectField label="Review Frequency" value={settings.review_frequency} options={["daily", "weekly", "adaptive"]} onChange={(value) => onPatch({ review_frequency: value })} />
      <SelectField label="Default Module" value={settings.default_learning_action || ""} options={["", "explain", "compare", "socratic", "derive", "exercise", "critic", "review", "no_ai_test"]} onChange={(value) => onPatch({ default_learning_action: value || null })} />
      <SelectField label="Output Language" value={settings.output_language} options={["zh", "en", "bilingual"]} onChange={(value) => onPatch({ output_language: value })} />
      <SelectField label="Mode" value={settings.exam_research_course_mode} options={["course", "exam", "research", "general"]} onChange={(value) => onPatch({ exam_research_course_mode: value })} />
      <ModuleChecklist settings={settings} onPatch={onPatch} />
    </section>
  );
}

function SystemSettingsTab({ settings, onPatch }: { settings: SystemSettings | null; onPatch: (patch: Partial<SystemSettings>) => void }) {
  if (!settings) return <EmptyState text="System settings are loading." />;
  return (
    <section className="settings-grid">
      <SelectField label="Default Language" value={settings.default_language} options={["zh", "en", "bilingual"]} onChange={(value) => onPatch({ default_language: value })} />
      <SelectField label="Default Model Routing" value={settings.default_model_routing} options={["fast", "medium", "strong"]} onChange={(value) => onPatch({ default_model_routing: value })} />
      <SelectField label="Response Style" value={settings.global_response_style} options={["concise", "guided", "deep"]} onChange={(value) => onPatch({ global_response_style: value })} />
      <SelectField label="Record Policy" value={settings.global_record_policy} options={["light", "medium", "heavy"]} onChange={(value) => onPatch({ global_record_policy: value })} />
      <SelectField label="Privacy Level" value={settings.privacy_level} options={["local", "selected_context", "provider_enabled"]} onChange={(value) => onPatch({ privacy_level: value })} />
      <ToggleField label="Auto State Update" checked={Boolean(settings.auto_state_update)} onChange={(checked) => onPatch({ auto_state_update: checked ? 1 : 0 })} />
      <SelectField label="Cost / Latency" value={settings.cost_latency_preference} options={["low_cost", "balanced", "low_latency", "quality"]} onChange={(value) => onPatch({ cost_latency_preference: value })} />
      <SelectField label="Notifications" value={settings.notification_preference} options={["none", "local", "daily_digest"]} onChange={(value) => onPatch({ notification_preference: value })} />
      <SelectField label="Theme" value={settings.theme} options={["light", "dark", "system"]} onChange={(value) => onPatch({ theme: value })} />
    </section>
  );
}

function LearningStateTab(props: {
  learningState: LearningStatePayload | null;
  references: ReferenceEntry[];
  referenceTitle: string;
  referenceText: string;
  onReferenceTitle: (value: string) => void;
  onReferenceText: (value: string) => void;
  onAddReference: () => void;
  onFile: (file: File) => void;
}) {
  const state = props.learningState;
  if (!state) return <EmptyState text="Learning state is loading." />;
  const repeatedConfusions = state.claims.filter((claim) => claim.status === "revised" || claim.epistemic_status === "wrong").slice(0, 4);
  return (
    <section className="state-panel">
      <StateGroup title="当前 Goal" items={state.temporal_traces.slice(0, 1)} primary="next_step" secondary="created_at" fallback="No recent goal trace." />
      <StateGroup title="核心 Claim" items={state.claims.slice(0, 4)} primary="normalized_statement" secondary="epistemic_status" fallback="No claims yet." />
      <StateGroup title="关键 Distinction" items={state.distinctions.slice(0, 4)} primary="boundary" secondary="concept_a" fallback="No distinctions yet." />
      <StateGroup title="反复误区" items={repeatedConfusions} primary="normalized_statement" secondary="status" fallback="No repeated confusion yet." />
      <StateGroup title="无 AI 内化区" items={state.knowledge_positions.slice(0, 4)} primary="concept" secondary="current_level" fallback="No no-AI items yet." />
      <StateGroup title="推导信任" items={state.derivation_trust_records.slice(0, 4)} primary="result_or_tool" secondary="no_ai_reconstruction_status" fallback="No derivation trust records yet." />
      <StateGroup title="回看点" items={state.review_triggers.slice(0, 4)} primary="target" secondary="status" fallback="No review triggers yet." />
      <StateGroup title="最近学习轨迹" items={state.temporal_traces.slice(0, 4)} primary="user_question" secondary="next_step" fallback="No learning trace yet." />
      <div className="reference-box">
        <h3><BookOpen size={16} /> Reference</h3>
        <input value={props.referenceTitle} placeholder="Reference title" onChange={(event) => props.onReferenceTitle(event.target.value)} />
        <textarea value={props.referenceText} placeholder="Paste reference text..." rows={5} onChange={(event) => props.onReferenceText(event.target.value)} />
        <div className="reference-actions">
          <button onClick={props.onAddReference}>保存 Reference</button>
          <label className="file-button">
            上传 txt/md/pdf
            <input type="file" accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf" onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void props.onFile(file);
            }} />
          </label>
        </div>
        <ul className="reference-list">
          {props.references.map((reference) => <li key={reference.id}>{reference.title}</li>)}
        </ul>
      </div>
    </section>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="field-row">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option} value={option}>{option || "none"}</option>)}
      </select>
    </label>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <label className="field-row">
      <span>{label}</span>
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          if (draft.trim() && draft !== value) onChange(draft.trim());
        }}
      />
    </label>
  );
}

function ToggleField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="toggle-row">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}

function ModuleChecklist({ settings, onPatch }: { settings: ProjectSettings; onPatch: (patch: Partial<ProjectSettings>) => void }) {
  const modules = ["explain", "compare", "socratic", "derive", "exercise", "critic", "review", "no_ai_test"];
  return (
    <div className="field-row">
      <span>Enabled Modules</span>
      <div className="module-grid">
        {modules.map((module) => {
          const checked = settings.enabled_modules.length === 0 || settings.enabled_modules.includes(module);
          return (
            <label key={module}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  const current = settings.enabled_modules.length === 0 ? modules : settings.enabled_modules;
                  const next = event.target.checked ? Array.from(new Set([...current, module])) : current.filter((item) => item !== module);
                  onPatch({ enabled_modules: next });
                }}
              />
              {module}
            </label>
          );
        })}
      </div>
    </div>
  );
}

function StateGroup({
  title,
  items,
  primary,
  secondary,
  fallback
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  primary: string;
  secondary?: string;
  fallback: string;
}) {
  return (
    <div className="state-group">
      <h3>{title}</h3>
      {items.length === 0 ? <p>{fallback}</p> : (
        <ul>
          {items.map((item) => (
            <li key={String(item.id)}>
              <span>{String(item[primary] || item.id)}</span>
              {secondary && item[secondary] ? <small>{formatStateMeta(secondary, item[secondary])}</small> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="empty-state">{text}</p>;
}

function summarizeUpdates(response: ChatResponse): string {
  const claims = response.state_updates.claims?.length || 0;
  const distinctions = response.state_updates.distinctions?.length || 0;
  const reviews = response.state_updates.review_triggers?.length || 0;
  const traces = response.state_updates.temporal_traces?.length || 0;
  const positions = response.state_updates.knowledge_positions?.length || 0;
  const derivations = response.state_updates.derivation_trust_records?.length || 0;
  const parts = [
    claims ? `${claims} Claim` : "",
    distinctions ? `${distinctions} 区分` : "",
    reviews ? `${reviews} 回看点` : "",
    positions ? `${positions} 内化位` : "",
    derivations ? `${derivations} 推导信任` : ""
  ].filter(Boolean);
  if (parts.length > 0) return `已更新 ${parts.join(" · ")}`;
  return traces ? "已记录本轮学习轨迹" : "本轮没有写入新的学习状态";
}

function summarizeRunNext(response: RunNextResponse): string {
  const priority = response.priority ? ` · ${response.priority}` : "";
  const action = response.expected_user_action || response.why_this_now || response.reason;
  return `${response.chosen_module}${priority} · ${truncate(action, 72)}`;
}

function formatStateMeta(key: string, value: unknown): string {
  const text = String(value);
  if (key.includes("created_at") || key.includes("updated_at") || key.includes("time")) return formatShortTime(text);
  return text;
}

function formatShortTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

export default App;

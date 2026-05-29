import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronRight,
  GitCompare,
  GraduationCap,
  History,
  Menu,
  MessageSquareText,
  PenLine,
  Play,
  Plus,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
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
        updateHint: summarizeUpdates(response)
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
        updateHint: `${response.chosen_module} · ${response.reason}`
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

  async function updateSystemSettings(patch: Partial<SystemSettings>) {
    setSystemSettings(await api.updateSystemSettings(patch));
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

  return (
    <div className="learn-shell">
      <TeachingRail activeAction={activeAction} onSelect={(action, mode) => { setActiveAction(action); setSelectedMode(mode); }} />
      <main className="chat-surface">
        <TopBar
          projects={projects}
          currentProject={currentProject}
          onProjectChange={setCurrentProjectId}
          onToggleDrawer={() => setDrawerOpen((value) => !value)}
        />
        <section className="message-list" aria-label="Conversation">
          {messages.map((message) => (
            <article className={`message-row ${message.role}`} key={message.id}>
              <div className="message-meta">{message.role === "user" ? "你" : "AI Learn OS"}{message.mode ? ` · ${message.mode}` : ""}</div>
              <div className="message-bubble">
                <MarkdownRenderer markdown={message.content} />
              </div>
              {message.updateHint && <div className="state-hint">{message.updateHint}</div>}
            </article>
          ))}
          <div ref={messageEndRef} />
        </section>
        {error && <div className="error-strip">{error}</div>}
        <Composer
          value={input}
          selectedMode={selectedMode}
          busy={busy}
          activeAction={activeAction}
          onChange={setInput}
          onSend={sendMessage}
          onRun={runNext}
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
  onToggleDrawer
}: {
  projects: Project[];
  currentProject: Project | null;
  onProjectChange: (id: string) => void;
  onToggleDrawer: () => void;
}) {
  return (
    <header className="top-bar">
      <div className="brand-mark">
        <Brain size={18} />
        <span>AI Learn OS</span>
      </div>
      <label className="project-select">
        <Target size={15} />
        <select value={currentProject?.id || ""} onChange={(event) => onProjectChange(event.target.value)}>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
      </label>
      <span className={`project-status ${currentProject?.status || "active"}`}>{currentProject?.status || "active"}</span>
      <button className="icon-control" onClick={onToggleDrawer} title="设置与学习状态">
        <Menu size={18} />
      </button>
    </header>
  );
}

function TeachingRail({
  activeAction,
  onSelect
}: {
  activeAction: ButtonAction | null;
  onSelect: (action: ButtonAction, mode: TeachingMode) => void;
}) {
  return (
    <aside className="teaching-rail" aria-label="教学动作">
      {actionButtons.map(({ action, mode, label, icon: Icon }) => (
        <button
          key={action}
          className={activeAction === action ? "rail-button active" : "rail-button"}
          onClick={() => onSelect(action, mode)}
          title={label}
        >
          <Icon size={17} />
          <span>{label}</span>
        </button>
      ))}
    </aside>
  );
}

function Composer({
  value,
  selectedMode,
  activeAction,
  busy,
  onChange,
  onSend,
  onRun
}: {
  value: string;
  selectedMode: TeachingMode;
  activeAction: ButtonAction | null;
  busy: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onRun: () => void;
}) {
  return (
    <footer className="composer-shell">
      <div className="mode-line">
        <span>当前模式：{activeAction || selectedMode}</span>
      </div>
      <div className="composer">
        <textarea
          value={value}
          placeholder="输入你想问的问题……"
          rows={2}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSend();
            }
          }}
        />
        <div className="composer-actions">
          <button className="icon-control strong" onClick={onSend} disabled={busy || !value.trim()} title="发送">
            <Send size={18} />
          </button>
          <button className="icon-control" onClick={onRun} disabled={busy} title="运行下一步">
            <Play size={18} />
          </button>
        </div>
      </div>
    </footer>
  );
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
        {props.tab === "project-settings" && <ProjectSettingsTab settings={props.projectSettings} onPatch={props.onProjectSettings} />}
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
  newProjectName: string;
  onNewProjectName: (value: string) => void;
  onCreateProject: () => void;
  onSelectProject: (id: string) => void;
}) {
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
              <small>{project.description || "No description"}</small>
            </span>
            <ChevronRight size={16} />
          </button>
        ))}
      </div>
    </section>
  );
}

function ProjectSettingsTab({ settings, onPatch }: { settings: ProjectSettings | null; onPatch: (patch: Partial<ProjectSettings>) => void }) {
  if (!settings) return <EmptyState text="Project settings will appear after selecting a project." />;
  return (
    <section className="settings-grid">
      <SelectField label="Learning Depth" value={settings.learning_depth} options={["light", "medium", "deep"]} onChange={(value) => onPatch({ learning_depth: value })} />
      <SelectField label="Teaching Style" value={settings.teaching_style} options={["concise", "socratic", "exam", "research"]} onChange={(value) => onPatch({ teaching_style: value })} />
      <SelectField label="Record Intensity" value={settings.record_intensity} options={["light", "medium", "heavy"]} onChange={(value) => onPatch({ record_intensity: value })} />
      <SelectField label="No-AI Strictness" value={settings.no_ai_strictness} options={["low", "medium", "high"]} onChange={(value) => onPatch({ no_ai_strictness: value })} />
      <SelectField label="Review Frequency" value={settings.review_frequency} options={["daily", "weekly", "adaptive"]} onChange={(value) => onPatch({ review_frequency: value })} />
      <SelectField label="Default Module" value={settings.default_learning_action || ""} options={["", "explain", "compare", "socratic", "derive", "exercise", "review"]} onChange={(value) => onPatch({ default_learning_action: value || null })} />
      <SelectField label="Output Language" value={settings.output_language} options={["zh", "en", "bilingual"]} onChange={(value) => onPatch({ output_language: value })} />
      <SelectField label="Mode" value={settings.exam_research_course_mode} options={["course", "exam", "research", "general"]} onChange={(value) => onPatch({ exam_research_course_mode: value })} />
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
  return (
    <section className="state-panel">
      <StateGroup title="当前 Goal" items={state.temporal_traces.slice(0, 2)} primary="next_step" fallback="No recent goal trace." />
      <StateGroup title="核心 Claim" items={state.claims.slice(0, 4)} primary="normalized_statement" fallback="No claims yet." />
      <StateGroup title="关键 Distinction" items={state.distinctions.slice(0, 4)} primary="boundary" fallback="No distinctions yet." />
      <StateGroup title="无 AI 内化区" items={state.knowledge_positions.slice(0, 4)} primary="concept" fallback="No no-AI items yet." />
      <StateGroup title="推导信任" items={state.derivation_trust_records.slice(0, 4)} primary="result_or_tool" fallback="No derivation trust records yet." />
      <StateGroup title="回看点" items={state.review_triggers.slice(0, 4)} primary="target" fallback="No review triggers yet." />
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

function StateGroup({ title, items, primary, fallback }: { title: string; items: Array<Record<string, unknown>>; primary: string; fallback: string }) {
  return (
    <div className="state-group">
      <h3>{title}</h3>
      {items.length === 0 ? <p>{fallback}</p> : (
        <ul>
          {items.map((item) => <li key={String(item.id)}>{String(item[primary] || item.id)}</li>)}
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
  return `已更新 ${claims} 条 Claim，${distinctions} 条概念区分，${reviews} 个回看点`;
}

export default App;

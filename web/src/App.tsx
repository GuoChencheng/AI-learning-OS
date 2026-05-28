import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import {
  Archive,
  BookOpen,
  Brain,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  FlaskConical,
  Home,
  Layers3,
  Milestone,
  SearchCheck,
  ShieldCheck,
  Target,
  Wrench
} from "lucide-react";
import { api } from "./api";
import { FormField } from "./components/FormField";
import { LearningCockpit } from "./components/LearningCockpit";
import { MarkdownRenderer } from "./components/MarkdownRenderer";
import { PageHeader } from "./components/PageHeader";
import { PromptPanel } from "./components/PromptPanel";
import { RecordTable } from "./components/RecordTable";
import { StatusBadge } from "./components/StatusBadge";
import { I18nContext, type InteractionMode, type Language, translations, useI18n } from "./i18n";
import type { DashboardView, LearningItemView, NextActionView, ProviderSettings, RecordItem } from "./types";
import { asText, listFromText, textFromList } from "./utils";

type PromptState = {
  title: string;
  prompt: string;
  description?: string;
  relatedRecordIds?: string[];
};

const nav = [
  ["/", Home, "dashboard"],
  ["/goals", Milestone, "goals"],
  ["/learning-items", Layers3, "learningItems"],
  ["/claims", SearchCheck, "claims"],
  ["/trust-tests", ShieldCheck, "trustTests"],
  ["/references", BookOpen, "references"],
  ["/reviews", ClipboardCheck, "reviews"],
  ["/advanced", Wrench, "advanced"]
] as const;

const claimTypes = ["definition", "analogy", "hypothesis", "connection", "calculation", "interpretation"];
const epistemicStatuses = [
  "strict_fact",
  "derived_result",
  "standard_interpretation",
  "heuristic",
  "analogy",
  "inference",
  "speculation",
  "learning_strategy",
  "wrong",
  "open_question"
];
const claimStatuses = ["unverified", "verified", "partially_correct", "misleading", "wrong", "open_question"];
const recordIntensities = ["light", "medium", "heavy"];
const readingStatuses = ["unread", "skimmed", "partial", "read", "archived"];
const testStatuses = ["planned", "generated", "attempted", "passed", "failed", "needs_retest"];
const testTypes = [
  "no_ai_explanation",
  "concept_distinction",
  "boundary_counterexample",
  "derivation_reconstruction",
  "mistake_diagnosis",
  "transfer_question",
  "delayed_retrieval",
  "mixed"
];
const internalizationTargets = ["A1", "A2", "A3", "A4"];
const positionLayers = ["A_no_ai_internalization", "B_knowledge_positioning", "C_index_recall"];
const toolRoles = ["core_tool", "non_core_tool", "none"];
const confidenceLevels = ["low", "medium", "high"];
const internalizationLevels = ["none", "A0", "A1", "A2", "A3", "A4"];
const derivationStatuses = ["not_started", "partial", "trusted", "needs_rederive"];
const derivationImportances = ["core_concept", "core_tool", "optional"];
const distinctionStatuses = ["needs_distinction", "partially_clear", "clear", "needs_test", "resolved", "needs_retest"];
const misconceptionStatuses = ["active", "corrected", "recurring", "archived"];
const misconceptionSeverities = ["minor", "important", "dangerous"];
const referenceTypes = ["textbook", "lecture_note", "paper", "review", "video", "webpage", "documentation", "other"];
const usageStages = ["initial_map", "core_learning", "later_reference", "optional"];
const visualTypes = ["paper_figure", "textbook_figure", "lecture_figure", "reliable_web_image", "reliable_web_video", "animation", "interactive", "ai_generated_schematic", "system_generated_diagram", "other"];
const visualSourcePriorities = ["paper_or_textbook", "reliable_web", "ai_generated", "system_generated"];
const reliabilities = ["high", "medium", "low"];
const visualUsages = ["explanation", "distinction", "derivation", "test", "review", "reference"];
const learningStates = [
  "totally_unclear",
  "name_only",
  "conceptually_confused",
  "nearby_concepts_confused",
  "feels_understood_but_cannot_explain",
  "formula_without_trust",
  "new_claim",
  "repeated_mistake",
  "mechanical_computation",
  "entering_core_topic",
  "ready_for_test",
  "too_much_material",
  "unknown_next_step"
];
const resourceByLearningType: Record<string, string> = {
  position: "positioning",
  distinction: "distinctions",
  misconception: "misconceptions",
  derivation: "derivations",
  test: "tests"
};

function useList(resource: string, query = "") {
  const [items, setItems] = useState<RecordItem[]>([]);
  const [error, setError] = useState("");
  const reload = () => api.list(resource, query).then((data) => setItems(data.items)).catch((err: Error) => setError(err.message));
  useEffect(() => {
    reload();
  }, [resource, query]);
  return { items, reload, error };
}

function Layout() {
  const { language, setLanguage, mode, setMode, providerAvailable, t } = useI18n();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <Brain size={22} />
          <span>AI Learning OS</span>
        </Link>
        <nav>
          {nav.map(([href, Icon, label]) => (
            <NavLink key={href} to={href} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon size={16} />
              {t(label)}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p className="side-note">{t("localState")}</p>
          <div className="sidebar-control">
            <span>{t("language")}</span>
            <div className="quiet-toggle">
              <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>English</button>
              <button className={language === "zh" ? "active" : ""} onClick={() => setLanguage("zh")}>中文</button>
            </div>
          </div>
          <div className="sidebar-control">
            <span>{t("mode")}</span>
            <div className="quiet-toggle">
              <button className={mode === "api" ? "active" : ""} disabled={!providerAvailable} title={providerAvailable ? "" : t("noProviderFallback")} onClick={() => setMode("api")}>{t("apiMode")}</button>
              <button className={mode === "prompt" ? "active" : ""} onClick={() => setMode("prompt")}>{t("promptMode")}</button>
            </div>
          </div>
          <Link to="/settings" className="sidebar-settings">{t("settings")}</Link>
        </div>
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/learning-items" element={<LearningItemsPage />} />
          <Route path="/claims" element={<ClaimsPage />} />
          <Route path="/trust-tests" element={<TrustTestsPage />} />
          <Route path="/references" element={<ReferencesPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/advanced" element={<AdvancedPage />} />
        </Routes>
      </main>
    </div>
  );
}

function Dashboard() {
  const { mode, providerAvailable, t } = useI18n();
  const [data, setData] = useState<DashboardView | null>(null);
  const [prompt, setPrompt] = useState<PromptState>({ title: "Prompt", prompt: "" });
  const reload = () => api.dashboardView().then(setData);

  useEffect(() => {
    reload();
  }, []);

  const generate = async (action: NextActionView) => {
    setPrompt(await promptForAction(action));
  };

  return (
    <>
      <LearningCockpit
        data={data}
        actionLabel={mode === "api" && providerAvailable ? t("runWithApi") : t("copyPrompt")}
        onPrimaryAction={generate}
      />
      {prompt.prompt && (
        <section className="mx-auto max-w-page px-gutter pb-10">
          <PromptPanel
            title={prompt.title}
            description={prompt.description || "Generated prompts are copied to external AI tools; provider runs remain optional."}
            prompt={prompt.prompt}
            relatedRecordIds={prompt.relatedRecordIds}
          />
        </section>
      )}
    </>
  );
}

async function promptForAction(action: NextActionView): Promise<PromptState> {
  const recordId = action.related_record_ids[0];
  if (action.action_type === "verify_claim" && recordId) {
    const result = await api.prompt("claim-verification", { claim_id: recordId });
    return { title: "Claim Verification Prompt", prompt: result.prompt, relatedRecordIds: [recordId] };
  }
  if (action.action_type === "rederive" && recordId) {
    const result = await api.prompt("derivation-guidance", { derivation_id: recordId });
    return { title: "Derivation Guidance Prompt", prompt: result.prompt, relatedRecordIds: [recordId] };
  }
  if (action.action_type === "resolve_confusion" && recordId) {
    const kind = recordId.startsWith("misc") ? "misconception-correction" : "distinction-test";
    const body = recordId.startsWith("misc") ? { misconception_id: recordId } : { distinction_id: recordId };
    const result = await api.prompt(kind, body);
    return { title: "Confusion Resolution Prompt", prompt: result.prompt, relatedRecordIds: [recordId] };
  }
  if (action.action_type === "test_topic") {
    if (recordId?.startsWith("test")) {
      const result = await api.prompt("test-record", { test_id: recordId });
      return { title: "Test Record Prompt", prompt: result.prompt, relatedRecordIds: [recordId] };
    }
    const topic = action.title.split(":").pop()?.trim() || action.title;
    const result = await api.prompt("test-topic", { topic });
    return { title: "Test Topic Prompt", prompt: result.prompt, relatedRecordIds: recordId ? [recordId] : [] };
  }
  if (action.action_type === "review_due") {
    const result = await api.prompt("weekly-review", {});
    return { title: "Weekly Review Prompt", prompt: result.prompt, relatedRecordIds: action.related_record_ids };
  }
  const result = await api.prompt("goal-intake", {});
  return { title: "Goal Intake Prompt", prompt: result.prompt, relatedRecordIds: action.related_record_ids };
}

function GoalsPage() {
  const { t } = useI18n();
  const { items, reload } = useList("goals");
  const { items: policies, reload: reloadPolicies } = useList("policies");
  const [active, setActive] = useState<RecordItem | null>(null);
  const [prompt, setPrompt] = useState<PromptState>({ title: "Goal Prompt", prompt: "" });
  const [form, setForm] = useState({ title: "", main_goal: "", stage_goal: "", transfer_goal: "", external_goal: "", priority_topics: "" });
  const [activeEdit, setActiveEdit] = useState({ title: "", main_goal: "", stage_goal: "", transfer_goal: "", external_goal: "", priority_topics: "" });
  const [policyForm, setPolicyForm] = useState({ title: "", description: "", a_zone_criteria: "", b_zone_criteria: "", c_zone_criteria: "", core_tool_criteria: "", non_core_tool_criteria: "", test_mode_criteria: "", upgrade_triggers: "", downgrade_triggers: "", revisit_triggers: "" });
  const [message, setMessage] = useState("");

  const refreshActive = () => api.activeGoal().then((result) => setActive(result.item)).catch(() => setActive(null));
  useEffect(() => {
    refreshActive();
  }, []);
  useEffect(() => {
    if (!active) return;
    setActiveEdit({
      title: asText(active.title),
      main_goal: asText(active.main_goal),
      stage_goal: asText(active.stage_goal),
      transfer_goal: asText(active.transfer_goal),
      external_goal: asText(active.external_goal),
      priority_topics: textFromList(active.priority_topics)
    });
  }, [active]);

  const save = async () => {
    setMessage("");
    const created = await api.create("goals", { ...form, priority_topics: listFromText(form.priority_topics), active: true });
    await api.setActiveGoal(created.item.id);
    await reload();
    await refreshActive();
    setForm({ title: "", main_goal: "", stage_goal: "", transfer_goal: "", external_goal: "", priority_topics: "" });
    setMessage("Created and activated goal.");
  };
  const saveActive = async () => {
    if (!active) return;
    setMessage("");
    const updated = await api.update("goals", active.id, { ...activeEdit, priority_topics: listFromText(activeEdit.priority_topics), active: true });
    setActive(updated.item);
    await reload();
    setMessage("Updated active goal.");
  };
  const generate = async (kind: "goal-intake" | "deep-research") => {
    const result = await api.prompt(kind, { goal_id: active?.id, raw_goal: form.main_goal || active?.main_goal });
    setPrompt({ title: kind === "goal-intake" ? "Goal Intake Prompt" : "Deep Research Prompt", prompt: result.prompt, relatedRecordIds: active ? [active.id] : [] });
  };
  const generatePolicyPrompt = async () => {
    if (!active) return;
    const result = await api.prompt("refine-policy", { goal_id: active.id });
    setPrompt({ title: "Refine Classification Policy Prompt", prompt: result.prompt, relatedRecordIds: [active.id] });
  };
  const savePolicy = async () => {
    if (!active) return;
    const created = await api.create("policies", {
      ...policyForm,
      a_zone_criteria: listFromText(policyForm.a_zone_criteria),
      b_zone_criteria: listFromText(policyForm.b_zone_criteria),
      c_zone_criteria: listFromText(policyForm.c_zone_criteria),
      core_tool_criteria: listFromText(policyForm.core_tool_criteria),
      non_core_tool_criteria: listFromText(policyForm.non_core_tool_criteria),
      test_mode_criteria: listFromText(policyForm.test_mode_criteria),
      upgrade_triggers: listFromText(policyForm.upgrade_triggers),
      downgrade_triggers: listFromText(policyForm.downgrade_triggers),
      revisit_triggers: listFromText(policyForm.revisit_triggers)
    });
    setPolicyForm({ title: "", description: "", a_zone_criteria: "", b_zone_criteria: "", c_zone_criteria: "", core_tool_criteria: "", non_core_tool_criteria: "", test_mode_criteria: "", upgrade_triggers: "", downgrade_triggers: "", revisit_triggers: "" });
    setMessage(`Created classification policy ${created.item.id}.`);
    await reloadPolicies();
  };
  const activePolicies = policies.filter((policy) => !active || policy.goal_id === active.id);

  return (
    <div className="page">
      <PageHeader title={t("goals")} description="Keep the active goal stack visible: why this matters, current stage, transfer target, and external constraints." />
      <section className="content-grid two">
        <section className="panel">
          <div className="card-kicker">Active Goal</div>
          {active ? <GoalSummary goal={active} /> : <p>No active goal selected.</p>}
          <div className="button-row">
            <button onClick={() => generate("goal-intake")}>{t("refineGoal")}</button>
            <button className="secondary" onClick={() => generate("deep-research")}>{t("deepResearch")}</button>
          </div>
          <details className="advanced-details">
            <summary>Edit active goal</summary>
            <div className="inline-form">
              <FormField label="Title" value={activeEdit.title} onChange={(title) => setActiveEdit({ ...activeEdit, title })} />
              <FormField label="Main goal" value={activeEdit.main_goal} onChange={(main_goal) => setActiveEdit({ ...activeEdit, main_goal })} textarea />
              <FormField label="Stage goal" value={activeEdit.stage_goal} onChange={(stage_goal) => setActiveEdit({ ...activeEdit, stage_goal })} textarea />
              <FormField label="Transfer goal" value={activeEdit.transfer_goal} onChange={(transfer_goal) => setActiveEdit({ ...activeEdit, transfer_goal })} textarea />
              <FormField label="External goal" value={activeEdit.external_goal} onChange={(external_goal) => setActiveEdit({ ...activeEdit, external_goal })} textarea />
              <FormField label="Priority topics" value={activeEdit.priority_topics} onChange={(priority_topics) => setActiveEdit({ ...activeEdit, priority_topics })} textarea />
              <button onClick={saveActive} disabled={!active}>Save active goal</button>
            </div>
          </details>
          <details className="advanced-details">
            <summary>{t("classificationPolicy")}</summary>
            <div className="button-row">
              <button className="secondary" onClick={generatePolicyPrompt} disabled={!active}>Refine Policy Prompt</button>
            </div>
            {activePolicies.length ? activePolicies.map((policy) => <RecordSummary key={policy.id} item={policy} fields={["title", "description", "a_zone_criteria", "test_mode_criteria", "revisit_triggers"]} />) : <p>No policy recorded.</p>}
            <details className="inline-details">
              <summary>Create policy</summary>
              <div className="inline-form">
                <FormField label="Title" value={policyForm.title} onChange={(title) => setPolicyForm({ ...policyForm, title })} />
                <FormField label="Description" value={policyForm.description} onChange={(description) => setPolicyForm({ ...policyForm, description })} textarea />
                <FormField label="A zone criteria" value={policyForm.a_zone_criteria} onChange={(a_zone_criteria) => setPolicyForm({ ...policyForm, a_zone_criteria })} textarea />
                <FormField label="B zone criteria" value={policyForm.b_zone_criteria} onChange={(b_zone_criteria) => setPolicyForm({ ...policyForm, b_zone_criteria })} textarea />
                <FormField label="C zone criteria" value={policyForm.c_zone_criteria} onChange={(c_zone_criteria) => setPolicyForm({ ...policyForm, c_zone_criteria })} textarea />
                <FormField label="Core tool criteria" value={policyForm.core_tool_criteria} onChange={(core_tool_criteria) => setPolicyForm({ ...policyForm, core_tool_criteria })} textarea />
                <FormField label="Non-core tool criteria" value={policyForm.non_core_tool_criteria} onChange={(non_core_tool_criteria) => setPolicyForm({ ...policyForm, non_core_tool_criteria })} textarea />
                <FormField label="Test mode criteria" value={policyForm.test_mode_criteria} onChange={(test_mode_criteria) => setPolicyForm({ ...policyForm, test_mode_criteria })} textarea />
                <FormField label="Upgrade triggers" value={policyForm.upgrade_triggers} onChange={(upgrade_triggers) => setPolicyForm({ ...policyForm, upgrade_triggers })} textarea />
                <FormField label="Downgrade triggers" value={policyForm.downgrade_triggers} onChange={(downgrade_triggers) => setPolicyForm({ ...policyForm, downgrade_triggers })} textarea />
                <FormField label="Revisit triggers" value={policyForm.revisit_triggers} onChange={(revisit_triggers) => setPolicyForm({ ...policyForm, revisit_triggers })} textarea />
                <button onClick={savePolicy} disabled={!active || !policyForm.title.trim() || !policyForm.description.trim()}>Create policy</button>
              </div>
            </details>
          </details>
          {message && <p className="save-message">{message}</p>}
        </section>
        {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} relatedRecordIds={prompt.relatedRecordIds} />}
      </section>
      <details className="panel form-panel add-learning-panel">
        <summary>{t("createNewGoal")}</summary>
        <FormField label="Title" value={form.title} onChange={(title) => setForm({ ...form, title })} />
        <FormField label="Main goal" value={form.main_goal} onChange={(main_goal) => setForm({ ...form, main_goal })} textarea />
        <FormField label="Stage goal" value={form.stage_goal} onChange={(stage_goal) => setForm({ ...form, stage_goal })} textarea />
        <FormField label="Transfer goal" value={form.transfer_goal} onChange={(transfer_goal) => setForm({ ...form, transfer_goal })} textarea />
        <FormField label="External goal" value={form.external_goal} onChange={(external_goal) => setForm({ ...form, external_goal })} textarea />
        <FormField label="Priority topics" value={form.priority_topics} onChange={(priority_topics) => setForm({ ...form, priority_topics })} textarea />
        <button onClick={save}>Create goal</button>
      </details>
      <section className="panel">
        <div className="goal-list">
          {items.map((goal) => (
            <article key={goal.id} className="list-card">
              <GoalSummary goal={goal} compact />
              <button className="secondary" onClick={() => api.setActiveGoal(goal.id).then(async (result) => { setActive(result.item); await reload(); })}>Set Active</button>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function LearningItemsPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<LearningItemView[]>([]);
  const [prompt, setPrompt] = useState<PromptState>({ title: "Learning Item Prompt", prompt: "" });
  const [message, setMessage] = useState("");
  const reload = () => api.learningItems().then((data) => setItems(data.items));
  useEffect(() => {
    reload();
  }, []);
  return (
    <div className="page">
      <PageHeader title={t("learningItems")} description="A human-facing view across positioning, distinctions, misconceptions, derivations, and tests. Source records remain separate." />
      <LearningItemCreatePanel onDone={async (nextMessage) => { setMessage(nextMessage); await reload(); }} />
      <MethodRouterPanel onPrompt={setPrompt} />
      {message && <p className="save-message">{message}</p>}
      <section className="content-grid two">
        <div className="learning-sections">
          <LearningItemSection title={t("mustInternalize")} items={items.filter((item) => (item.position || "").startsWith("A_") || ["A0", "A1", "A2", "A3", "A4"].includes(item.internalization_level || ""))} onPrompt={setPrompt} onRefresh={reload} />
          <LearningItemSection title={t("needClarification")} items={items.filter((item) => ["distinction", "misconception"].includes(item.source_type))} onPrompt={setPrompt} onRefresh={reload} />
          <LearningItemSection title={t("needTrust")} items={items.filter((item) => item.source_type === "derivation" && item.status !== "trusted")} onPrompt={setPrompt} onRefresh={reload} />
          <LearningItemSection title={t("dueOverdue")} items={items.filter((item) => item.temporal_status || ["needs_retest", "failed", "planned"].includes(item.status))} onPrompt={setPrompt} onRefresh={reload} />
          <LearningItemSection title={t("laterIndex")} items={items.filter((item) => (item.position || "").startsWith("C_") || item.record_intensity === "light")} onPrompt={setPrompt} onRefresh={reload} />
        </div>
        {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} description={prompt.description} relatedRecordIds={prompt.relatedRecordIds} />}
      </section>
    </div>
  );
}

function ClaimsPage() {
  const { t } = useI18n();
  const { items, reload } = useList("claims");
  const [prompt, setPrompt] = useState<PromptState>({ title: "Claim Verification Prompt", prompt: "" });
  const [form, setForm] = useState({
    text: "",
    context: "",
    type: "hypothesis",
    status: "unverified",
    epistemic_status: "speculation",
    record_intensity: "light",
    strict_part: "",
    caveat: "",
    counterexample_or_boundary: "",
    next_action: ""
  });
  const [editing, setEditing] = useState<Record<string, Record<string, string>>>({});
  const [message, setMessage] = useState("");
  const addClaim = async () => {
    const created = await api.create("claims", form);
    setForm({ text: "", context: "", type: "hypothesis", status: "unverified", epistemic_status: "speculation", record_intensity: "light", strict_part: "", caveat: "", counterexample_or_boundary: "", next_action: "" });
    setMessage(`Created claim ${created.item.id}.`);
    await reload();
  };
  const update = async (claim: RecordItem, status: string) => {
    await api.update("claims", claim.id, { status });
    await reload();
  };
  const patchClaim = async (claim: RecordItem, payload: Record<string, unknown>) => {
    await api.update("claims", claim.id, payload);
    setEditing((current) => {
      const next = { ...current };
      delete next[claim.id];
      return next;
    });
    await reload();
  };
  const gen = async (claim: RecordItem) => {
    const result = await api.prompt("claim-verification", { claim_id: claim.id });
    setPrompt({ title: "Claim Verification Prompt", prompt: result.prompt, description: "Claims are learner-generated ideas, not AI facts.", relatedRecordIds: [claim.id] });
  };
  return (
    <div className="page">
      <PageHeader title={t("claims")} description="Epistemic verification for learner-generated claims. Facts, analogies, interpretations, and speculation stay visibly separate." />
      <details className="panel add-learning-panel">
        <summary>{t("addClaim")}</summary>
        <div className="inline-form">
          <FormField label="Claim text" value={form.text} onChange={(text) => setForm({ ...form, text })} textarea />
          <FormField label="Context" value={form.context} onChange={(context) => setForm({ ...form, context })} textarea />
          <FormField label="Type" value={form.type} onChange={(type) => setForm({ ...form, type })} options={claimTypes} />
          <FormField label="Status" value={form.status} onChange={(status) => setForm({ ...form, status })} options={claimStatuses} />
          <FormField label="Epistemic status" value={form.epistemic_status} onChange={(epistemic_status) => setForm({ ...form, epistemic_status })} options={epistemicStatuses} />
          <FormField label="Intensity" value={form.record_intensity} onChange={(record_intensity) => setForm({ ...form, record_intensity })} options={recordIntensities} />
          <FormField label="Strict part" value={form.strict_part} onChange={(strict_part) => setForm({ ...form, strict_part })} textarea />
          <FormField label="Caveat" value={form.caveat} onChange={(caveat) => setForm({ ...form, caveat })} textarea />
          <FormField label="Boundary / counterexample" value={form.counterexample_or_boundary} onChange={(counterexample_or_boundary) => setForm({ ...form, counterexample_or_boundary })} textarea />
          <FormField label="Next action" value={form.next_action} onChange={(next_action) => setForm({ ...form, next_action })} textarea />
        </div>
        <button onClick={addClaim} disabled={!form.text.trim()}>Create claim</button>
      </details>
      {message && <p className="save-message">{message}</p>}
      <section className="content-grid two">
        <div className="claim-grid">
          {items.map((claim) => (
            <article key={claim.id} className="panel claim-card">
              <div className="card-kicker">{t("learnerClaim")}</div>
              <h2>{asText(claim.text)}</h2>
              <p>{asText(claim.context)}</p>
              <div className="badge-row">
                <StatusBadge value={claim.status} />
                <StatusBadge value={claim.epistemic_status} />
                <StatusBadge value={claim.record_intensity} />
              </div>
              <RecordSummary item={claim} fields={["strict_part", "caveat", "counterexample_or_boundary", "next_action"]} />
              <div className="button-row">
                <button onClick={() => gen(claim)}>{t("generatePrompt")}</button>
                <button className="secondary" onClick={() => update(claim, "verified")}>{t("markVerified")}</button>
                <button className="secondary" onClick={() => update(claim, "partially_correct")}>Partially Correct</button>
                <button className="secondary" onClick={() => update(claim, "misleading")}>Misleading</button>
                <button className="secondary" onClick={() => update(claim, "wrong")}>Wrong</button>
              </div>
              <details className="inline-details">
                <summary>Edit verification fields</summary>
                <ClaimEditFields
                  claim={claim}
                  draft={editing[claim.id] || {}}
                  onChange={(draft) => setEditing({ ...editing, [claim.id]: draft })}
                  onSave={(payload) => patchClaim(claim, payload)}
                />
              </details>
            </article>
          ))}
        </div>
        {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} description={prompt.description} relatedRecordIds={prompt.relatedRecordIds} />}
      </section>
    </div>
  );
}

function ClaimEditFields({
  claim,
  draft,
  onChange,
  onSave
}: {
  claim: RecordItem;
  draft: Record<string, string>;
  onChange: (draft: Record<string, string>) => void;
  onSave: (payload: Record<string, unknown>) => void;
}) {
  const value = (key: string) => draft[key] ?? asText(claim[key]);
  const set = (key: string, next: string) => onChange({ ...draft, [key]: next });
  const payload = {
    type: value("type"),
    status: value("status"),
    epistemic_status: value("epistemic_status"),
    record_intensity: value("record_intensity"),
    strict_part: value("strict_part"),
    caveat: value("caveat"),
    counterexample_or_boundary: value("counterexample_or_boundary"),
    next_action: value("next_action")
  };
  return (
    <div className="inline-form">
      <FormField label="Type" value={value("type")} onChange={(next) => set("type", next)} options={claimTypes} />
      <FormField label="Status" value={value("status")} onChange={(next) => set("status", next)} options={claimStatuses} />
      <FormField label="Epistemic status" value={value("epistemic_status")} onChange={(next) => set("epistemic_status", next)} options={epistemicStatuses} />
      <FormField label="Intensity" value={value("record_intensity")} onChange={(next) => set("record_intensity", next)} options={recordIntensities} />
      <FormField label="Strict part" value={value("strict_part")} onChange={(next) => set("strict_part", next)} textarea />
      <FormField label="Caveat" value={value("caveat")} onChange={(next) => set("caveat", next)} textarea />
      <FormField label="Boundary / counterexample" value={value("counterexample_or_boundary")} onChange={(next) => set("counterexample_or_boundary", next)} textarea />
      <FormField label="Next action" value={value("next_action")} onChange={(next) => set("next_action", next)} textarea />
      <button onClick={() => onSave(payload)}>Save claim fields</button>
    </div>
  );
}

function TrustTestsPage() {
  const { t } = useI18n();
  const { items: derivations, reload: reloadDerivations } = useList("derivations");
  const { items: tests, reload: reloadTests } = useList("tests");
  const [prompt, setPrompt] = useState<PromptState>({ title: "Trust / Test Prompt", prompt: "" });
  const [derivationForm, setDerivationForm] = useState({ topic: "", importance: "core_tool", status: "not_started", result_to_trust: "", user_derived_steps: "", ai_hinted_steps: "", not_yet_trusted: "", next_action: "", record_intensity: "light" });
  const [testForm, setTestForm] = useState({ topic: "", test_type: "mixed", status: "planned", internalization_target: "A2", prompt: "", learner_answer: "", feedback: "", next_retest_at: "" });
  const [message, setMessage] = useState("");
  const [testSuggestions, setTestSuggestions] = useState<string[]>([]);

  const genDerivation = async (derivation: RecordItem) => {
    const result = await api.prompt("derivation-guidance", { derivation_id: derivation.id });
    setPrompt({ title: "Derivation Guidance Prompt", prompt: result.prompt, relatedRecordIds: [derivation.id] });
  };
  const genTest = async (test: RecordItem) => {
    const result = await api.prompt("test-record", { test_id: test.id });
    setPrompt({ title: "Test Record Prompt", prompt: result.prompt, relatedRecordIds: [test.id] });
  };
  const addDerivation = async () => {
    const created = await api.create("derivations", {
      ...derivationForm,
      user_derived_steps: listFromText(derivationForm.user_derived_steps),
      ai_hinted_steps: listFromText(derivationForm.ai_hinted_steps),
      not_yet_trusted: listFromText(derivationForm.not_yet_trusted)
    });
    setDerivationForm({ topic: "", importance: "core_tool", status: "not_started", result_to_trust: "", user_derived_steps: "", ai_hinted_steps: "", not_yet_trusted: "", next_action: "", record_intensity: "light" });
    setMessage(`Created derivation ${created.item.id}.`);
    await reloadDerivations();
  };
  const addTest = async () => {
    const payload = { ...testForm, learner_answer: testForm.learner_answer || null, feedback: testForm.feedback || null, next_retest_at: testForm.next_retest_at || null };
    const created = await api.create("tests", payload);
    setTestForm({ topic: "", test_type: "mixed", status: "planned", internalization_target: "A2", prompt: "", learner_answer: "", feedback: "", next_retest_at: "" });
    setMessage(`Created test ${created.item.id}.`);
    await reloadTests();
  };
  const reloadBoth = async () => {
    await Promise.all([reloadDerivations(), reloadTests()]);
  };

  return (
    <div className="page">
      <PageHeader title={t("trustTests")} description="Build trust in results, then test internalization. AI can hint, but the learner must reconstruct and retrieve." />
      <section className="ladder rich-ladder">
        {["A0 important, not verified", "A1 explain and distinguish", "A2 boundary/counterexample", "A3 reconstruct/derive/transfer", "A4 delayed retrieval"].map((step) => <span key={step}>{step}</span>)}
      </section>
      <section className="panel compact utility-strip">
        <div>
          <div className="card-kicker">{t("readyForTest")}</div>
          <p>Use deterministic local records to find topics that need test mode.</p>
        </div>
        <button className="secondary" onClick={() => api.testSuggestions().then((data) => setTestSuggestions(data.items))}>{t("suggestTests")}</button>
      </section>
      {!!testSuggestions.length && (
        <ul className="mini-list suggestion-list">
          {testSuggestions.slice(0, 8).map((suggestion) => <li key={suggestion}>{suggestion}</li>)}
        </ul>
      )}
      <details className="panel add-learning-panel">
        <summary>{t("addDerivationOrTest")}</summary>
        <div className="content-grid two">
          <section className="sub-card">
            <h3>Add Derivation Trust Record</h3>
            <div className="inline-form">
              <FormField label="Topic" value={derivationForm.topic} onChange={(topic) => setDerivationForm({ ...derivationForm, topic })} />
              <FormField label="Importance" value={derivationForm.importance} onChange={(importance) => setDerivationForm({ ...derivationForm, importance })} options={derivationImportances} />
              <FormField label="Status" value={derivationForm.status} onChange={(status) => setDerivationForm({ ...derivationForm, status })} options={derivationStatuses} />
              <FormField label="Intensity" value={derivationForm.record_intensity} onChange={(record_intensity) => setDerivationForm({ ...derivationForm, record_intensity })} options={recordIntensities} />
              <FormField label="Result to trust" value={derivationForm.result_to_trust} onChange={(result_to_trust) => setDerivationForm({ ...derivationForm, result_to_trust })} textarea />
              <FormField label="User-derived steps" value={derivationForm.user_derived_steps} onChange={(user_derived_steps) => setDerivationForm({ ...derivationForm, user_derived_steps })} textarea />
              <FormField label="AI-hinted steps" value={derivationForm.ai_hinted_steps} onChange={(ai_hinted_steps) => setDerivationForm({ ...derivationForm, ai_hinted_steps })} textarea />
              <FormField label="Not yet trusted" value={derivationForm.not_yet_trusted} onChange={(not_yet_trusted) => setDerivationForm({ ...derivationForm, not_yet_trusted })} textarea />
              <FormField label="Next action" value={derivationForm.next_action} onChange={(next_action) => setDerivationForm({ ...derivationForm, next_action })} textarea />
            </div>
            <button onClick={addDerivation} disabled={!derivationForm.topic.trim() || !derivationForm.result_to_trust.trim()}>Create derivation</button>
          </section>
          <section className="sub-card">
            <h3>Add Test Mode Record</h3>
            <div className="inline-form">
              <FormField label="Topic" value={testForm.topic} onChange={(topic) => setTestForm({ ...testForm, topic })} />
              <FormField label="Test type" value={testForm.test_type} onChange={(test_type) => setTestForm({ ...testForm, test_type })} options={testTypes} />
              <FormField label="Status" value={testForm.status} onChange={(status) => setTestForm({ ...testForm, status })} options={testStatuses} />
              <FormField label="Internalization target" value={testForm.internalization_target} onChange={(internalization_target) => setTestForm({ ...testForm, internalization_target })} options={internalizationTargets} />
              <FormField label="Prompt" value={testForm.prompt} onChange={(promptValue) => setTestForm({ ...testForm, prompt: promptValue })} textarea />
              <FormField label="Learner answer" value={testForm.learner_answer} onChange={(learner_answer) => setTestForm({ ...testForm, learner_answer })} textarea />
              <FormField label="Feedback" value={testForm.feedback} onChange={(feedback) => setTestForm({ ...testForm, feedback })} textarea />
              <FormField label="Next retest at" value={testForm.next_retest_at} onChange={(next_retest_at) => setTestForm({ ...testForm, next_retest_at })} />
            </div>
            <button onClick={addTest} disabled={!testForm.topic.trim()}>Create test</button>
          </section>
        </div>
      </details>
      {message && <p className="save-message">{message}</p>}
      <section className="content-grid two">
        <section>
          <h2 className="section-heading">{t("derivationTrust")}</h2>
          <div className="card-stack">
            {derivations.map((derivation) => (
              <article key={derivation.id} className="panel trust-card">
                <div className="panel-title-row">
                  <h2>{asText(derivation.topic)}</h2>
                  <StatusBadge value={derivation.status} />
                </div>
                <p><strong>Result:</strong> {asText(derivation.result_to_trust)}</p>
                <Checklist title="User-derived" items={derivation.user_derived_steps} />
                <Checklist title="AI-hinted" items={derivation.ai_hinted_steps} />
                <Checklist title="Not yet trusted" items={derivation.not_yet_trusted} warn />
                <p>{asText(derivation.next_action)}</p>
                <div className="button-row">
                  <button onClick={() => genDerivation(derivation)}>{t("generatePrompt")}</button>
                  <button className="secondary" onClick={() => api.update("derivations", derivation.id, { status: "trusted", trusted_at: new Date().toISOString() }).then(reloadDerivations)}>Mark Trusted</button>
                  <button className="secondary" onClick={() => api.create("tests", { topic: derivation.topic, test_type: "derivation_reconstruction", status: "planned", internalization_target: "A3", prompt: "" }).then(reloadTests)}>Send to Test</button>
                </div>
                <details className="inline-details">
                  <summary>Edit trust record</summary>
                  <DerivationEditFields derivation={derivation} onSave={async (payload) => { await api.update("derivations", derivation.id, payload); await reloadDerivations(); }} />
                </details>
              </article>
            ))}
          </div>
        </section>
        <section>
          <h2 className="section-heading">{t("testMode")}</h2>
          <div className="card-stack">
            {tests.map((test) => (
              <article key={test.id} className="panel test-card">
                <div className="panel-title-row">
                  <h2>{asText(test.topic)}</h2>
                  <StatusBadge value={test.status} />
                </div>
                <div className="badge-row">
                  <StatusBadge value={test.test_type} />
                  <StatusBadge value={test.internalization_target} />
                  {Boolean(asText(test.next_retest_at)) && <StatusBadge value="due" />}
                </div>
                <RecordSummary item={test} fields={["prompt", "learner_answer", "feedback", "next_retest_at"]} />
                <div className="button-row">
                  <button onClick={() => genTest(test)}>{t("generatePrompt")}</button>
                  <button className="secondary" onClick={() => api.update("tests", test.id, { status: "passed", passed_at: new Date().toISOString() }).then(reloadTests)}>Passed</button>
                  <button className="secondary" onClick={() => api.update("tests", test.id, { status: "failed", failed_at: new Date().toISOString() }).then(reloadTests)}>Failed</button>
                  <button className="secondary" onClick={() => api.update("tests", test.id, { status: "needs_retest" }).then(reloadTests)}>Needs Retest</button>
                </div>
                <details className="inline-details">
                  <summary>Edit test result</summary>
                  <TestEditFields test={test} onSave={async (payload) => { await api.update("tests", test.id, payload); await reloadBoth(); }} />
                </details>
              </article>
            ))}
          </div>
        </section>
      </section>
      {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} relatedRecordIds={prompt.relatedRecordIds} />}
    </div>
  );
}

function DerivationEditFields({ derivation, onSave }: { derivation: RecordItem; onSave: (payload: Record<string, unknown>) => void }) {
  const [draft, setDraft] = useState({
    importance: asText(derivation.importance),
    status: asText(derivation.status),
    record_intensity: asText(derivation.record_intensity || "light"),
    result_to_trust: asText(derivation.result_to_trust),
    user_derived_steps: textFromList(derivation.user_derived_steps),
    ai_hinted_steps: textFromList(derivation.ai_hinted_steps),
    not_yet_trusted: textFromList(derivation.not_yet_trusted),
    next_action: asText(derivation.next_action)
  });
  const payload = {
    ...draft,
    user_derived_steps: listFromText(draft.user_derived_steps),
    ai_hinted_steps: listFromText(draft.ai_hinted_steps),
    not_yet_trusted: listFromText(draft.not_yet_trusted),
    trusted_at: draft.status === "trusted" ? new Date().toISOString() : derivation.trusted_at || null
  };
  return (
    <div className="inline-form">
      <FormField label="Importance" value={draft.importance} onChange={(importance) => setDraft({ ...draft, importance })} options={derivationImportances} />
      <FormField label="Status" value={draft.status} onChange={(status) => setDraft({ ...draft, status })} options={derivationStatuses} />
      <FormField label="Intensity" value={draft.record_intensity} onChange={(record_intensity) => setDraft({ ...draft, record_intensity })} options={recordIntensities} />
      <FormField label="Result to trust" value={draft.result_to_trust} onChange={(result_to_trust) => setDraft({ ...draft, result_to_trust })} textarea />
      <FormField label="User-derived steps" value={draft.user_derived_steps} onChange={(user_derived_steps) => setDraft({ ...draft, user_derived_steps })} textarea />
      <FormField label="AI-hinted steps" value={draft.ai_hinted_steps} onChange={(ai_hinted_steps) => setDraft({ ...draft, ai_hinted_steps })} textarea />
      <FormField label="Not yet trusted" value={draft.not_yet_trusted} onChange={(not_yet_trusted) => setDraft({ ...draft, not_yet_trusted })} textarea />
      <FormField label="Next action" value={draft.next_action} onChange={(next_action) => setDraft({ ...draft, next_action })} textarea />
      <button onClick={() => onSave(payload)}>Save derivation</button>
    </div>
  );
}

function TestEditFields({ test, onSave }: { test: RecordItem; onSave: (payload: Record<string, unknown>) => void }) {
  const [draft, setDraft] = useState({
    test_type: asText(test.test_type),
    status: asText(test.status),
    internalization_target: asText(test.internalization_target),
    prompt: asText(test.prompt),
    learner_answer: asText(test.learner_answer),
    feedback: asText(test.feedback),
    next_retest_at: asText(test.next_retest_at)
  });
  const now = new Date().toISOString();
  const payload = {
    ...draft,
    learner_answer: draft.learner_answer || null,
    feedback: draft.feedback || null,
    next_retest_at: draft.next_retest_at || null,
    attempted_at: ["attempted", "passed", "failed", "needs_retest"].includes(draft.status) ? now : test.attempted_at || null,
    passed_at: draft.status === "passed" ? now : test.passed_at || null,
    failed_at: draft.status === "failed" ? now : test.failed_at || null
  };
  return (
    <div className="inline-form">
      <FormField label="Test type" value={draft.test_type} onChange={(test_type) => setDraft({ ...draft, test_type })} options={testTypes} />
      <FormField label="Status" value={draft.status} onChange={(status) => setDraft({ ...draft, status })} options={testStatuses} />
      <FormField label="Internalization target" value={draft.internalization_target} onChange={(internalization_target) => setDraft({ ...draft, internalization_target })} options={internalizationTargets} />
      <FormField label="Prompt" value={draft.prompt} onChange={(promptValue) => setDraft({ ...draft, prompt: promptValue })} textarea />
      <FormField label="Learner answer" value={draft.learner_answer} onChange={(learner_answer) => setDraft({ ...draft, learner_answer })} textarea />
      <FormField label="Feedback" value={draft.feedback} onChange={(feedback) => setDraft({ ...draft, feedback })} textarea />
      <FormField label="Next retest at" value={draft.next_retest_at} onChange={(next_retest_at) => setDraft({ ...draft, next_retest_at })} />
      <button onClick={() => onSave(payload)}>Save test</button>
    </div>
  );
}

function ReferencesPage() {
  const { t } = useI18n();
  const { items: refs, reload } = useList("references");
  const [imports, setImports] = useState<RecordItem[]>([]);
  const [selectedImport, setSelectedImport] = useState<RecordItem | null>(null);
  const [prompt, setPrompt] = useState<PromptState>({ title: "Reference Prompt", prompt: "" });
  const [form, setForm] = useState({ title: "", authors_or_source: "", reference_type: "other", path_or_url: "", topics: "", relevance_to_goal: "", usage_stage: "initial_map", reading_status: "unread", notes: "" });
  const [visualForm, setVisualForm] = useState({ topic: "", title: "", visual_type: "reliable_web_image", source_priority: "reliable_web", source_url_or_path: "", source_detail: "", reliability: "medium", usage: "explanation", why_needed: "", related_record_ids: "", copyright_note: "" });
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.researchImports().then((data) => setImports(data.items));
  }, []);

  const add = async () => {
    const created = await api.create("references", { ...form, topics: listFromText(form.topics) });
    setForm({ title: "", authors_or_source: "", reference_type: "other", path_or_url: "", topics: "", relevance_to_goal: "", usage_stage: "initial_map", reading_status: "unread", notes: "" });
    setMessage(`Added reference ${created.item.id}.`);
    await reload();
  };
  const importPrompt = async (kind: "extract-references" | "extract-positioning") => {
    if (!selectedImport) return;
    const result = await api.prompt(kind, { import_id: selectedImport.id });
    setPrompt({ title: kind === "extract-references" ? "Extract References Prompt" : "Extract Positioning Prompt", prompt: result.prompt, relatedRecordIds: [selectedImport.id] });
  };
  const visualPrompt = async (topic: string) => {
    const result = await api.prompt("visual-suggest", { topic });
    setPrompt({ title: "Visual Suggestion Prompt", prompt: result.prompt, relatedRecordIds: [] });
  };
  const addVisual = async () => {
    const created = await api.create("visuals", { ...visualForm, related_record_ids: listFromText(visualForm.related_record_ids) });
    setVisualForm({ topic: "", title: "", visual_type: "reliable_web_image", source_priority: "reliable_web", source_url_or_path: "", source_detail: "", reliability: "medium", usage: "explanation", why_needed: "", related_record_ids: "", copyright_note: "" });
    setMessage(`Added visual metadata ${created.item.id}.`);
  };

  return (
    <div className="page">
      <PageHeader title={t("references")} description={t("deepResearchHelper")} />
      <section className="reference-grid">
        {refs.map((ref) => (
          <article className="panel reference-card" key={ref.id}>
            <div className="panel-title-row">
              <h2>{asText(ref.title)}</h2>
              <StatusBadge value={ref.reading_status} />
            </div>
            <div className="badge-row">
              <StatusBadge value={ref.reference_type} />
              <StatusBadge value={ref.usage_stage} />
            </div>
            <p>{asText(ref.relevance_to_goal)}</p>
            <p><strong>Topics:</strong> {asText(ref.topics)}</p>
            <a href={referenceHref(ref)} target="_blank" rel="noreferrer">Open source</a>
            <code>{asText(ref.path_or_url)}</code>
            <div className="button-row">
              <button className="secondary" onClick={() => api.update("references", ref.id, { reading_status: "read" }).then(reload)}>Mark Read</button>
              <button className="secondary" onClick={() => api.update("references", ref.id, { reading_status: "partial" }).then(reload)}>Mark Partial</button>
              <button className="secondary" onClick={() => visualPrompt(asText((ref.topics as unknown[])?.[0] || ref.title))}>{t("generatePrompt")}</button>
            </div>
            <details className="inline-details">
              <summary>Edit reference</summary>
              <ReferenceEditFields reference={ref} onSave={async (payload) => { await api.update("references", ref.id, payload); await reload(); }} />
            </details>
          </article>
        ))}
        {!refs.length && <section className="panel empty-panel">No references yet. Import Deep Research or add a source.</section>}
      </section>
      {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} relatedRecordIds={prompt.relatedRecordIds} />}
      <details className="panel form-panel add-learning-panel">
          <summary>{t("addReference")}</summary>
          <div className="inline-form">
            <FormField label="Title" value={form.title} onChange={(title) => setForm({ ...form, title })} />
            <FormField label="Authors / source" value={form.authors_or_source} onChange={(authors_or_source) => setForm({ ...form, authors_or_source })} />
            <FormField label="Reference type" value={form.reference_type} onChange={(reference_type) => setForm({ ...form, reference_type })} options={referenceTypes} />
            <FormField label="Path or URL" value={form.path_or_url} onChange={(path_or_url) => setForm({ ...form, path_or_url })} />
            <FormField label="Topics" value={form.topics} onChange={(topics) => setForm({ ...form, topics })} textarea />
            <FormField label="Relevance to goal" value={form.relevance_to_goal} onChange={(relevance_to_goal) => setForm({ ...form, relevance_to_goal })} textarea />
            <FormField label="Usage stage" value={form.usage_stage} onChange={(usage_stage) => setForm({ ...form, usage_stage })} options={usageStages} />
            <FormField label="Reading status" value={form.reading_status} onChange={(reading_status) => setForm({ ...form, reading_status })} options={readingStatuses} />
            <FormField label="Notes" value={form.notes} onChange={(notes) => setForm({ ...form, notes })} textarea />
          </div>
          <button onClick={add}>Add Reference</button>
          {message && <p className="save-message">{message}</p>}
      </details>
      <details className="panel advanced-details">
        <summary>Deep Research Imports</summary>
        <RecordTable items={imports} columns={["name", "path"]} onSelect={setSelectedImport} selectedId={selectedImport?.id} />
        <div className="button-row">
          <button className="secondary" disabled={!selectedImport} onClick={() => importPrompt("extract-references")}>Extract References</button>
          <button className="secondary" disabled={!selectedImport} onClick={() => importPrompt("extract-positioning")}>Extract Positioning</button>
        </div>
        {selectedImport && <MarkdownRenderer markdown={asText(selectedImport.markdown)} />}
      </details>
      <details className="panel advanced-details">
        <summary>Add visual resource metadata</summary>
        <p className="prompt-purpose">Store only visual metadata and learning purpose. Do not download copyrighted materials automatically.</p>
        <div className="inline-form">
          <FormField label="Topic" value={visualForm.topic} onChange={(topic) => setVisualForm({ ...visualForm, topic })} />
          <FormField label="Title" value={visualForm.title} onChange={(title) => setVisualForm({ ...visualForm, title })} />
          <FormField label="Visual type" value={visualForm.visual_type} onChange={(visual_type) => setVisualForm({ ...visualForm, visual_type })} options={visualTypes} />
          <FormField label="Source priority" value={visualForm.source_priority} onChange={(source_priority) => setVisualForm({ ...visualForm, source_priority })} options={visualSourcePriorities} />
          <FormField label="Source URL or path" value={visualForm.source_url_or_path} onChange={(source_url_or_path) => setVisualForm({ ...visualForm, source_url_or_path })} />
          <FormField label="Source detail" value={visualForm.source_detail} onChange={(source_detail) => setVisualForm({ ...visualForm, source_detail })} textarea />
          <FormField label="Reliability" value={visualForm.reliability} onChange={(reliability) => setVisualForm({ ...visualForm, reliability })} options={reliabilities} />
          <FormField label="Usage" value={visualForm.usage} onChange={(usage) => setVisualForm({ ...visualForm, usage })} options={visualUsages} />
          <FormField label="Why needed" value={visualForm.why_needed} onChange={(why_needed) => setVisualForm({ ...visualForm, why_needed })} textarea />
          <FormField label="Related record IDs" value={visualForm.related_record_ids} onChange={(related_record_ids) => setVisualForm({ ...visualForm, related_record_ids })} textarea />
          <FormField label="Copyright note" value={visualForm.copyright_note} onChange={(copyright_note) => setVisualForm({ ...visualForm, copyright_note })} textarea />
        </div>
        <button onClick={addVisual} disabled={!visualForm.topic.trim() || !visualForm.title.trim() || !visualForm.why_needed.trim()}>Add visual metadata</button>
      </details>
    </div>
  );
}

function ReferenceEditFields({ reference, onSave }: { reference: RecordItem; onSave: (payload: Record<string, unknown>) => void }) {
  const [draft, setDraft] = useState({
    title: asText(reference.title),
    authors_or_source: asText(reference.authors_or_source),
    reference_type: asText(reference.reference_type),
    path_or_url: asText(reference.path_or_url),
    topics: textFromList(reference.topics),
    relevance_to_goal: asText(reference.relevance_to_goal),
    usage_stage: asText(reference.usage_stage),
    reading_status: asText(reference.reading_status),
    notes: asText(reference.notes)
  });
  const payload = { ...draft, topics: listFromText(draft.topics) };
  return (
    <div className="inline-form">
      <FormField label="Title" value={draft.title} onChange={(title) => setDraft({ ...draft, title })} />
      <FormField label="Authors / source" value={draft.authors_or_source} onChange={(authors_or_source) => setDraft({ ...draft, authors_or_source })} />
      <FormField label="Reference type" value={draft.reference_type} onChange={(reference_type) => setDraft({ ...draft, reference_type })} options={referenceTypes} />
      <FormField label="Path or URL" value={draft.path_or_url} onChange={(path_or_url) => setDraft({ ...draft, path_or_url })} />
      <FormField label="Topics" value={draft.topics} onChange={(topics) => setDraft({ ...draft, topics })} textarea />
      <FormField label="Relevance to goal" value={draft.relevance_to_goal} onChange={(relevance_to_goal) => setDraft({ ...draft, relevance_to_goal })} textarea />
      <FormField label="Usage stage" value={draft.usage_stage} onChange={(usage_stage) => setDraft({ ...draft, usage_stage })} options={usageStages} />
      <FormField label="Reading status" value={draft.reading_status} onChange={(reading_status) => setDraft({ ...draft, reading_status })} options={readingStatuses} />
      <FormField label="Notes" value={draft.notes} onChange={(notes) => setDraft({ ...draft, notes })} textarea />
      <button onClick={() => onSave(payload)}>Save reference</button>
    </div>
  );
}

function ReviewsPage() {
  const { t } = useI18n();
  const [reviews, setReviews] = useState<RecordItem[]>([]);
  const [selected, setSelected] = useState<RecordItem | null>(null);
  const [prompt, setPrompt] = useState<PromptState>({ title: "Weekly Review Prompt", prompt: "" });
  const reload = () => api.reviews().then((data) => {
    setReviews(data.items);
    setSelected((current) => current || data.items[0] || null);
  });
  useEffect(() => {
    reload();
  }, []);
  const generate = async () => {
    const result = await api.generateReview();
    await reload();
    setSelected({ id: result.path, path: result.path, markdown: result.markdown, name: result.path });
  };
  const genPrompt = async () => {
    const result = await api.prompt("weekly-review", {});
    setPrompt({ title: "Weekly Review Prompt", prompt: result.prompt });
  };
  return (
    <div className="page">
      <PageHeader title={t("reviews")} description="Action-oriented weekly summaries: claims, trust gaps, distinctions, due reviews, references, and next week actions." />
      <section className="review-hero">
        <section className="panel">
          <div className="panel-title-row">
            <h2>{t("latestReview")}</h2>
            <div className="button-row">
              <button onClick={generate}>{t("generateWeeklyReview")}</button>
              <button className="secondary" onClick={genPrompt}>{t("reviewPrompt")}</button>
            </div>
          </div>
          <ReviewActionSummary markdown={asText(selected?.markdown)} />
        </section>
        {prompt.prompt && <PromptPanel title={prompt.title} prompt={prompt.prompt} />}
      </section>
      <section className="panel review-markdown">
        <MarkdownRenderer markdown={asText(selected?.markdown)} />
      </section>
      <details className="panel advanced-details">
        <summary>{t("reviewHistory")}</summary>
        <div className="review-list">
          {reviews.slice(0, 5).map((review) => (
            <button className={`review-button ${selected?.id === review.id ? "active" : ""}`} key={review.id} onClick={() => setSelected(review)}>
              <FileText size={16} />
              {asText(review.name)}
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}

function ReviewActionSummary({ markdown }: { markdown: string }) {
  const lines = markdown
    .split(/\n/)
    .map((line) => line.replace(/^[-*#\s]+/, "").trim())
    .filter((line) => /action|next|verify|test|review|trust|rederive|复|验证|测试|信任/i.test(line))
    .slice(0, 3);
  return (
    <ul className="mini-list">
      {lines.length ? lines.map((line) => <li key={line}>{line}</li>) : <li>No review selected yet.</li>}
    </ul>
  );
}

function SettingsPage() {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [message, setMessage] = useState("");
  const [runs, setRuns] = useState<RecordItem[]>([]);
  useEffect(() => {
    api.providerSettings().then(setSettings);
    api.aiRuns().then((data) => setRuns(data.items)).catch(() => setRuns([]));
  }, []);
  const testProvider = async (providerId: string) => {
    setMessage(`Testing ${providerId}...`);
    try {
      const result = await api.providerTest(providerId);
      setMessage(result.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Provider test failed.");
    }
  };
  return (
    <div className="page">
      <PageHeader title="Settings / Providers" description="Prompt-only mode is the default. Connected mode is optional and sends only selected prompts or context packs." />
      <section className="content-grid two">
        <section className="panel">
          <div className="card-kicker">Privacy Mode</div>
          <h2>{settings?.prompt_only === false ? "Connected mode configured" : "Prompt-only default"}</h2>
          <p className="privacy-warning">Connected mode sends selected context to your configured model provider. Prompt-only mode sends nothing.</p>
          <RecordSummary
            item={{
              id: "settings",
              timezone: settings?.timezone,
              default_provider: settings?.default_provider || "none",
              default_model: settings?.default_model || "provider default",
              context_budget: settings?.context_budget,
              ui: `${settings?.ui_host || "127.0.0.1"}:${settings?.ui_port || 8765}`
            }}
            fields={["timezone", "default_provider", "default_model", "context_budget", "ui"]}
          />
        </section>
        <section className="panel">
          <div className="card-kicker">Provider Safety</div>
          <ul className="mini-list">
            <li>API keys should live in environment variables.</li>
            <li>The UI never displays key values.</li>
            <li>AI results are saved as artifacts, not source-of-truth records.</li>
            <li>No prompt is sent unless you explicitly run it.</li>
          </ul>
          {message && <pre className="debug-box">{message}</pre>}
        </section>
      </section>
      <section className="provider-grid">
        {(settings?.providers || []).length ? settings?.providers.map((provider) => (
          <article className="panel provider-card" key={provider.id}>
            <div className="panel-title-row">
              <h2>{provider.id}</h2>
              <StatusBadge value={provider.is_default ? "default" : provider.type} />
            </div>
            <RecordSummary
              item={{
                id: provider.id,
                type: provider.type,
                base_url: provider.base_url,
                default_model: provider.default_model || "",
                api_key_env: provider.api_key_env || "none",
                api_key_present: provider.api_key_present ? "set" : "not set"
              }}
              fields={["type", "base_url", "default_model", "api_key_env", "api_key_present"]}
            />
            <button className="secondary" onClick={() => testProvider(provider.id)}>Test Provider</button>
          </article>
        )) : (
          <section className="panel">
            <h2>No providers configured</h2>
            <p>Copy <code>config.example.yaml</code> to <code>config.yaml</code> and store real keys in environment variables.</p>
          </section>
        )}
      </section>
      <details className="panel advanced-details">
        <summary>AI Run Artifacts</summary>
        <RecordTable items={runs} columns={["id", "provider", "model", "prompt_type", "user_review_status", "created_at"]} />
      </details>
    </div>
  );
}

function AdvancedPage() {
  const { items: sessions } = useList("sessions");
  const { items: events } = useList("events");
  const { items: policies } = useList("policies");
  const { items: visuals } = useList("visuals");
  const [validation, setValidation] = useState("");
  const [indexText, setIndexText] = useState("");
  const [contextPolicy, setContextPolicy] = useState("");

  const validate = async () => {
    const result = await api.validate();
    setValidation(result.ok ? "Validation passed." : result.errors.join("\n"));
  };
  const loadIndexes = async () => {
    const [summary, openLoops, recent, policy] = await Promise.all([api.indexes(), api.indexMarkdown("open-loops"), api.indexMarkdown("recent"), api.contextPolicy()]);
    setIndexText(`${summary.summary}\n\n${openLoops.markdown}\n\n${recent.markdown}`);
    setContextPolicy(policy.policy);
  };

  return (
    <div className="page">
      <PageHeader title="Advanced" description="Raw metadata, context packs, indexes, events, policies, visuals, validation, and debugging tools for power users and Codex." />
      <section className="content-grid two">
        <section className="panel">
          <h2>Debug Tools</h2>
          <div className="button-row">
            <button onClick={validate}>Validate</button>
            <button className="secondary" onClick={loadIndexes}>Load Indexes</button>
          </div>
          <pre className="debug-box">{validation || "Run validation to inspect errors."}</pre>
        </section>
        <section className="panel">
          <h2>Context Policy</h2>
          <pre className="debug-box">{contextPolicy || "Load indexes to show context loading policy."}</pre>
        </section>
      </section>
      <details className="panel advanced-details"><summary>Indexes</summary><pre className="debug-box">{indexText || "Load indexes first."}</pre></details>
      <details className="panel advanced-details"><summary>Raw Sessions</summary><RecordTable items={sessions} columns={["id", "topic", "learning_state", "created_at"]} /></details>
      <details className="panel advanced-details"><summary>Event Logs</summary><RecordTable items={events} columns={["event_type", "target_type", "target_id", "summary", "timestamp_local"]} /></details>
      <details className="panel advanced-details"><summary>Policies</summary><RecordTable items={policies} columns={["id", "title", "description", "updated_at"]} /></details>
      <details className="panel advanced-details"><summary>Visual Resources</summary><RecordTable items={visuals} columns={["id", "topic", "title", "visual_type", "usage", "reliability"]} /></details>
      <details className="panel advanced-details">
        <summary>Provider settings</summary>
        <p className="prompt-purpose">Optional connected mode remains off by default. API keys are never displayed.</p>
        <Link to="/settings" className="text-link">Open provider settings</Link>
      </details>
    </div>
  );
}

function LearningItemCreatePanel({ onDone }: { onDone: (message: string) => void }) {
  const { t } = useI18n();
  const [kind, setKind] = useState("position");
  const [position, setPosition] = useState({
    knowledge_point: "",
    position: "B_knowledge_positioning",
    tool_role: "none",
    reason: "",
    confidence: "medium",
    epistemic_status: "learning_strategy",
    revisit_when: "",
    record_intensity: "light",
    internalization_level: "none"
  });
  const [distinction, setDistinction] = useState({
    title: "",
    concepts: "",
    confusion_statement: "",
    status: "needs_distinction",
    record_intensity: "light",
    internalization_target: "none",
    next_action: ""
  });
  const [misconception, setMisconception] = useState({
    statement: "",
    why_wrong: "",
    corrected_view: "",
    related_topics: "",
    severity: "important",
    status: "active",
    next_action: ""
  });

  const create = async () => {
    if (kind === "position") {
      const created = await api.create("positioning", { ...position, revisit_when: listFromText(position.revisit_when) });
      setPosition({ ...position, knowledge_point: "", reason: "", revisit_when: "" });
      onDone(`Created positioning item ${created.item.id}.`);
      return;
    }
    if (kind === "distinction") {
      const created = await api.create("distinctions", { ...distinction, concepts: listFromText(distinction.concepts) });
      setDistinction({ ...distinction, title: "", concepts: "", confusion_statement: "", next_action: "" });
      onDone(`Created distinction ${created.item.id}.`);
      return;
    }
    const created = await api.create("misconceptions", { ...misconception, related_topics: listFromText(misconception.related_topics) });
    setMisconception({ ...misconception, statement: "", why_wrong: "", corrected_view: "", related_topics: "", next_action: "" });
    onDone(`Created misconception ${created.item.id}.`);
  };
  const canCreate =
    (kind === "position" && position.knowledge_point.trim() && position.reason.trim()) ||
    (kind === "distinction" && distinction.title.trim() && distinction.confusion_statement.trim()) ||
    (kind === "misconception" && misconception.statement.trim() && misconception.why_wrong.trim() && misconception.corrected_view.trim());

  return (
    <details className="panel add-learning-panel">
      <summary>{t("addLearningItem")}</summary>
      <div className="segmented-row">
        {["position", "distinction", "misconception"].map((option) => (
          <button key={option} className={kind === option ? "" : "secondary"} onClick={() => setKind(option)}>{option}</button>
        ))}
      </div>
      {kind === "position" && (
        <div className="inline-form">
          <FormField label="Knowledge point" value={position.knowledge_point} onChange={(knowledge_point) => setPosition({ ...position, knowledge_point })} />
          <FormField label="Position" value={position.position} onChange={(value) => setPosition({ ...position, position: value })} options={positionLayers} />
          <FormField label="Tool role" value={position.tool_role} onChange={(tool_role) => setPosition({ ...position, tool_role })} options={toolRoles} />
          <FormField label="Confidence" value={position.confidence} onChange={(confidence) => setPosition({ ...position, confidence })} options={confidenceLevels} />
          <FormField label="Epistemic status" value={position.epistemic_status} onChange={(epistemic_status) => setPosition({ ...position, epistemic_status })} options={epistemicStatuses} />
          <FormField label="Internalization level" value={position.internalization_level} onChange={(internalization_level) => setPosition({ ...position, internalization_level })} options={internalizationLevels} />
          <FormField label="Intensity" value={position.record_intensity} onChange={(record_intensity) => setPosition({ ...position, record_intensity })} options={recordIntensities} />
          <FormField label="Reason / next handling" value={position.reason} onChange={(reason) => setPosition({ ...position, reason })} textarea />
          <FormField label="Revisit triggers" value={position.revisit_when} onChange={(revisit_when) => setPosition({ ...position, revisit_when })} textarea />
        </div>
      )}
      {kind === "distinction" && (
        <div className="inline-form">
          <FormField label="Title" value={distinction.title} onChange={(title) => setDistinction({ ...distinction, title })} />
          <FormField label="Concepts" value={distinction.concepts} onChange={(concepts) => setDistinction({ ...distinction, concepts })} textarea />
          <FormField label="Confusion statement" value={distinction.confusion_statement} onChange={(confusion_statement) => setDistinction({ ...distinction, confusion_statement })} textarea />
          <FormField label="Status" value={distinction.status} onChange={(status) => setDistinction({ ...distinction, status })} options={distinctionStatuses} />
          <FormField label="Internalization target" value={distinction.internalization_target} onChange={(internalization_target) => setDistinction({ ...distinction, internalization_target })} options={internalizationLevels} />
          <FormField label="Intensity" value={distinction.record_intensity} onChange={(record_intensity) => setDistinction({ ...distinction, record_intensity })} options={recordIntensities} />
          <FormField label="Next action" value={distinction.next_action} onChange={(next_action) => setDistinction({ ...distinction, next_action })} textarea />
        </div>
      )}
      {kind === "misconception" && (
        <div className="inline-form">
          <FormField label="Statement" value={misconception.statement} onChange={(statement) => setMisconception({ ...misconception, statement })} textarea />
          <FormField label="Why wrong" value={misconception.why_wrong} onChange={(why_wrong) => setMisconception({ ...misconception, why_wrong })} textarea />
          <FormField label="Corrected view" value={misconception.corrected_view} onChange={(corrected_view) => setMisconception({ ...misconception, corrected_view })} textarea />
          <FormField label="Related topics" value={misconception.related_topics} onChange={(related_topics) => setMisconception({ ...misconception, related_topics })} textarea />
          <FormField label="Severity" value={misconception.severity} onChange={(severity) => setMisconception({ ...misconception, severity })} options={misconceptionSeverities} />
          <FormField label="Status" value={misconception.status} onChange={(status) => setMisconception({ ...misconception, status })} options={misconceptionStatuses} />
          <FormField label="Next action" value={misconception.next_action} onChange={(next_action) => setMisconception({ ...misconception, next_action })} textarea />
        </div>
      )}
      <button onClick={create} disabled={!canCreate}>Create {kind}</button>
    </details>
  );
}

function MethodRouterPanel({ onPrompt }: { onPrompt: (prompt: PromptState) => void }) {
  const { t } = useI18n();
  const [state, setState] = useState("unknown_next_step");
  const [topic, setTopic] = useState("");
  const [actions, setActions] = useState<string[]>([]);
  const [rationale, setRationale] = useState("");
  const suggest = async () => {
    const result = await api.methodSuggest(state);
    setActions(result.actions);
    setRationale(result.rationale);
  };
  const generate = async () => {
    const result = await api.prompt("method-router", { state, topic });
    setActions(result.actions || []);
    setRationale("Generated a method-routing prompt for the selected learning state.");
    onPrompt({ title: "Method Router Prompt", prompt: result.prompt, description: "Ask AI to choose a learning method without teaching the whole topic unless requested.", relatedRecordIds: [] });
  };
  return (
    <details className="panel add-learning-panel">
      <summary>{t("methodRouter")}</summary>
      <div className="method-router-grid">
        <FormField label="Learning state" value={state} onChange={setState} options={learningStates} />
        <FormField label="Topic" value={topic} onChange={setTopic} placeholder="Optional topic" />
      </div>
      <div className="button-row">
        <button className="secondary" onClick={suggest}>Suggest local methods</button>
        <button onClick={generate}>{t("generatePrompt")}</button>
      </div>
      {(actions.length || rationale) && (
        <div className="method-result">
          {rationale && <p>{rationale}</p>}
          <div className="badge-row">{actions.map((action) => <StatusBadge key={action} value={action} />)}</div>
        </div>
      )}
    </details>
  );
}

function LearningItemSection({ title, items, onPrompt, onRefresh }: { title: string; items: LearningItemView[]; onPrompt: (prompt: PromptState) => void; onRefresh: () => void }) {
  const uniqueItems = useMemo(() => Array.from(new Map(items.map((item) => [item.id, item])).values()).slice(0, 12), [items]);
  return (
    <details className="panel learning-section" open>
      <summary className="section-summary">
        <h2>{title}</h2>
        <strong>{uniqueItems.length}</strong>
      </summary>
      {uniqueItems.length ? uniqueItems.map((item) => <LearningItemMini key={item.id} item={item} onPrompt={onPrompt} onRefresh={onRefresh} />) : <p>No items in this section.</p>}
    </details>
  );
}

function LearningItemMini({ item, onPrompt, onRefresh }: { item: LearningItemView; onPrompt: (prompt: PromptState) => void; onRefresh: () => void }) {
  const { t } = useI18n();
  const generate = async () => {
    let result;
    if (item.source_type === "distinction") result = await api.prompt("distinction-test", { distinction_id: item.id });
    else if (item.source_type === "misconception") result = await api.prompt("misconception-correction", { misconception_id: item.id });
    else if (item.source_type === "derivation") result = await api.prompt("derivation-guidance", { derivation_id: item.id });
    else if (item.source_type === "test") result = await api.prompt("test-record", { test_id: item.id });
    else result = await api.prompt("dynamic-positioning", { knowledge_point: item.title, current_context: item.next_action });
    onPrompt({ title: `${item.title} Prompt`, prompt: result.prompt, relatedRecordIds: [item.id] });
  };
  const resource = resourceByLearningType[item.source_type];
  const sendToTest = async () => {
    await api.create("tests", {
      topic: item.title,
      position_id: item.source_type === "position" ? item.id : undefined,
      test_type: item.source_type === "distinction" ? "concept_distinction" : item.source_type === "derivation" ? "derivation_reconstruction" : "mixed",
      status: "planned",
      internalization_target: internalizationTargets.includes(item.internalization_level || "") ? item.internalization_level : "A2",
      prompt: ""
    });
    await onRefresh();
  };
  const markReviewed = async () => {
    if (!resource) return;
    await api.update(resource, item.id, { last_reviewed_at: new Date().toISOString() });
    await onRefresh();
  };
  const markProgress = async () => {
    if (!resource) return;
    if (item.source_type === "position") {
      const ladder = ["none", "A0", "A1", "A2", "A3", "A4"];
      const index = Math.max(0, ladder.indexOf(item.internalization_level || "none"));
      await api.update(resource, item.id, { internalization_level: ladder[Math.min(index + 1, ladder.length - 1)], last_touched_at: new Date().toISOString() });
    } else if (item.source_type === "distinction") {
      await api.update(resource, item.id, { status: item.status === "needs_distinction" ? "partially_clear" : "needs_test", last_distinguished_at: new Date().toISOString() });
    } else if (item.source_type === "misconception") {
      await api.update(resource, item.id, { status: "corrected", corrected_at: new Date().toISOString() });
    } else if (item.source_type === "derivation") {
      await api.update(resource, item.id, { status: "trusted", trusted_at: new Date().toISOString() });
    } else if (item.source_type === "test") {
      await api.update(resource, item.id, { status: "passed", passed_at: new Date().toISOString() });
    }
    await onRefresh();
  };
  return (
    <article className="learning-item">
      <div>
        <strong>{item.title}</strong>
        <div className="badge-row">
          <StatusBadge value={item.source_type} />
          <StatusBadge value={item.status} />
          {item.internalization_level && <StatusBadge value={item.internalization_level} />}
          {item.record_intensity && <StatusBadge value={item.record_intensity} />}
          {item.temporal_status && <StatusBadge value={item.temporal_status} />}
        </div>
        {item.next_action && <p>{item.next_action}</p>}
      </div>
      <div className="button-row">
        <button className="secondary" onClick={generate}>{t("generatePrompt")}</button>
        <details className="more-actions">
          <summary>{t("more")}</summary>
          <button className="secondary" onClick={sendToTest}>{t("sendToTest")}</button>
          <button className="secondary" disabled={!resource} onClick={markReviewed}>{t("markReviewed")}</button>
          <button className="secondary" disabled={!resource} onClick={markProgress}>{t("markProgress")}</button>
        </details>
        <details className="inline-details">
          <summary>Details</summary>
          <RecordSummary item={(item.source || {}) as RecordItem} fields={detailFieldsForItem(item)} />
          <details className="advanced-details"><summary>Raw record</summary><pre>{JSON.stringify(item.source, null, 2)}</pre></details>
        </details>
      </div>
    </article>
  );
}

function detailFieldsForItem(item: LearningItemView): string[] {
  if (item.source_type === "position") return ["knowledge_point", "position", "tool_role", "internalization_level", "reason", "revisit_when"];
  if (item.source_type === "distinction") return ["title", "concepts", "confusion_statement", "distinguishing_criteria", "boundary_cases", "next_action"];
  if (item.source_type === "misconception") return ["statement", "why_wrong", "corrected_view", "related_topics", "next_action"];
  if (item.source_type === "derivation") return ["topic", "result_to_trust", "user_derived_steps", "not_yet_trusted", "next_action"];
  if (item.source_type === "test") return ["topic", "test_type", "prompt", "learner_answer", "feedback", "next_retest_at"];
  return ["id", "status", "next_action"];
}

function GoalSummary({ goal, compact = false }: { goal: RecordItem; compact?: boolean }) {
  return (
    <div className={compact ? "goal-summary compact" : "goal-summary"}>
      <h2>{asText(goal.title)}</h2>
      <p>{asText(goal.main_goal)}</p>
      <dl>
        <div><dt>Stage</dt><dd>{asText(goal.stage_goal) || "Not recorded"}</dd></div>
        <div><dt>Transfer</dt><dd>{asText(goal.transfer_goal) || "Not recorded"}</dd></div>
        {!compact && <div><dt>External</dt><dd>{asText(goal.external_goal) || "Not recorded"}</dd></div>}
        {!compact && <div><dt>Priority topics</dt><dd>{asText(goal.priority_topics) || "None recorded"}</dd></div>}
      </dl>
    </div>
  );
}

function RecordSummary({ item, fields }: { item: RecordItem; fields: string[] }) {
  return (
    <dl className="summary-list">
      {fields.map((field) => (
        <div key={field}>
          <dt>{field.replace(/_/g, " ")}</dt>
          <dd>{asText(item[field]) || "Not recorded"}</dd>
        </div>
      ))}
    </dl>
  );
}

function Checklist({ title, items, warn = false }: { title: string; items: unknown; warn?: boolean }) {
  const list = Array.isArray(items) ? items.map(asText) : listFromText(asText(items));
  return (
    <div className="checklist">
      <h3>{title}</h3>
      <ul>
        {list.length ? list.map((item) => <li key={item}><CheckCircle2 size={14} className={warn ? "warn-icon" : ""} />{item}</li>) : <li><Archive size={14} />None recorded.</li>}
      </ul>
    </div>
  );
}

function referenceHref(ref: RecordItem): string {
  const path = asText(ref.path_or_url);
  if (/^https?:/.test(path)) return path;
  return `/files/${path.split("/").map(encodeURIComponent).join("/")}`;
}

export default function App() {
  const [language, setLanguageState] = useState<Language>(() => (localStorage.getItem("ailearn.language") === "zh" ? "zh" : "en"));
  const [mode, setModeState] = useState<InteractionMode>(() => (localStorage.getItem("ailearn.mode") === "prompt" ? "prompt" : "api"));
  const [providerAvailable, setProviderAvailable] = useState(false);

  useEffect(() => {
    api.providerSettings()
      .then((settings) => {
        const available = settings.providers.length > 0;
        setProviderAvailable(available);
        if (!available) setModeState("prompt");
      })
      .catch(() => {
        setProviderAvailable(false);
        setModeState("prompt");
      });
  }, []);

  const setLanguage = (next: Language) => {
    setLanguageState(next);
    localStorage.setItem("ailearn.language", next);
  };
  const setMode = (next: InteractionMode) => {
    const resolved = next === "api" && !providerAvailable ? "prompt" : next;
    setModeState(resolved);
    localStorage.setItem("ailearn.mode", resolved);
  };
  const t = (key: keyof typeof translations.en) => translations[language][key] || translations.en[key];

  return (
    <I18nContext.Provider value={{ language, setLanguage, mode, setMode, providerAvailable, t }}>
      <Layout />
    </I18nContext.Provider>
  );
}

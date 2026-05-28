import { Link } from "react-router-dom";
import type { DashboardView, LearningItemView, NextActionView } from "../types";
import { useI18n, type Language } from "../i18n";
import { asText } from "../utils";

type PromptModeLabel = "Run with API" | "Copy Prompt" | string;

type LearningCockpitProps = {
  data: DashboardView | null;
  actionLabel: PromptModeLabel;
  onPrimaryAction: (action: NextActionView) => void;
  onSecondaryAction?: (action: NextActionView) => void;
};

const openLoopLabels: Record<Language, Record<string, string>> = {
  en: {
    unverified_claims: "Unverified claims",
    weak_claims: "Weak claims",
    trust_gaps: "Trust gaps",
    confusions: "Confusions",
    misconceptions: "Misconceptions",
    due_tests: "Due tests",
    due_reviews: "Due reviews"
  },
  zh: {
    unverified_claims: "未验证判断",
    weak_claims: "薄弱判断",
    trust_gaps: "信任缺口",
    confusions: "混淆",
    misconceptions: "错误观念",
    due_tests: "到期测试",
    due_reviews: "到期复盘"
  }
};

export function LearningCockpit({
  data,
  actionLabel,
  onPrimaryAction,
  onSecondaryAction = onPrimaryAction
}: LearningCockpitProps) {
  const { language, t } = useI18n();
  const goal = data?.active_goal;
  const primary = data?.primary_next_action;
  const secondary = data?.secondary_next_actions || [];
  const loops = visibleOpenLoops(data?.open_loop_counts || {});
  const readyForTest = data?.ready_for_test || [];
  const trustGapCount = data?.open_loop_counts?.trust_gaps || data?.trust_gaps?.length || 0;

  return (
    <div className="min-h-[calc(100vh-3rem)] px-gutter py-10 md:py-14">
      <section className="mx-auto grid max-w-page grid-cols-1 gap-12 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          <header className="max-w-[980px]">
            {goal ? (
              <>
                <p className="mb-4 text-meta font-semibold uppercase text-muted">{t("activeGoal")}</p>
                <h1 className="m-0 max-w-[13ch] font-display text-[clamp(3rem,9vw,7.5rem)] font-semibold leading-[0.92] tracking-normal text-ink">
                  {asText(goal.title)}
                </h1>
                <p className="mt-7 max-w-readable text-[clamp(1.125rem,2vw,1.75rem)] leading-[1.22] text-muted">
                  {asText(goal.main_goal)}
                </p>
              </>
            ) : (
              <ZenBlank
                title={t("noActiveGoal")}
                body="A cockpit is empty until a goal gives it gravity."
                className="min-h-[46vh]"
              />
            )}
          </header>

          <section className="mt-14 max-w-[900px] md:mt-20" aria-labelledby="primary-next-action">
            <p className="mb-5 text-meta font-semibold uppercase text-muted">{t("primaryNextAction")}</p>
            {primary ? (
              <div className="border-t border-ink pt-8">
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
                  <span className="font-mono text-meta text-muted">{formatPriority(primary.priority)}</span>
                  <span className="text-meta font-semibold uppercase text-muted">{formatActionType(primary.action_type)}</span>
                </div>
                <h2 id="primary-next-action" className="m-0 mt-5 max-w-[16ch] font-display text-[clamp(2rem,5vw,4.75rem)] font-semibold leading-[0.98] tracking-normal text-ink">
                  {primary.title}
                </h2>
                {primary.reason && (
                  <p className="mt-6 max-w-readable text-body text-muted">{primary.reason}</p>
                )}
                <button className="mt-9 min-h-11 px-5 text-caption" onClick={() => onPrimaryAction(primary)}>
                  {actionLabel}
                </button>
              </div>
            ) : (
              <ZenBlank title={t("noNextAction")} body="No forced motion. Review, read, or start a new session when the next question appears." />
            )}
          </section>

          <OpenLoopTicker loops={loops} language={language} />

          {!!secondary.length && (
            <section className="mt-12 max-w-readable border-t border-line pt-5" aria-label="Secondary next actions">
              <p className="mb-4 text-meta font-semibold uppercase text-muted">After this</p>
              <div className="grid gap-3">
                {secondary.slice(0, 3).map((action) => (
                  <button
                    key={action.id}
                    className="group min-h-0 justify-between border-0 border-b border-line bg-white px-0 py-3 text-left text-ink hover:bg-white"
                    onClick={() => onSecondaryAction(action)}
                  >
                    <span className="max-w-[34rem] text-caption font-medium">{action.title}</span>
                    <span className="text-meta text-muted group-hover:text-ink">{formatActionType(action.action_type)}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="grid content-start gap-10 pt-1 xl:border-l xl:border-line xl:pl-8">
          <SideMetric label={t("trustGaps")} value={trustGapCount} tone={trustGapCount ? "trust" : "quiet"} />
          <ReadyForTestList items={readyForTest} />
          <RecentActivityList items={data?.recent_activity || []} />
        </aside>
      </section>
    </div>
  );
}

function OpenLoopTicker({ loops, language }: { loops: Array<[string, number]>; language: Language }) {
  if (!loops.length) {
    return (
      <section className="mt-14 max-w-[900px] border-t border-line pt-5">
        <ZenBlank title={language === "zh" ? "暂无未闭合事项" : "No open loops"} body="The surface stays quiet until something needs attention." compact />
      </section>
    );
  }

  return (
    <section className="mt-14 max-w-[900px] border-t border-line pt-5" aria-label="Open loop counts">
      <dl className="grid grid-cols-2 gap-x-8 gap-y-5 sm:flex sm:flex-wrap sm:items-end">
        {loops.map(([key, count]) => (
          <div key={key} className="min-w-[9rem]">
            <dt className="text-meta font-medium text-muted">{loopLabel(key, language)}</dt>
            <dd className="m-0 mt-1 font-display text-[2rem] font-semibold leading-none text-ink">{count}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function SideMetric({ label, value, tone = "quiet" }: { label: string; value: number; tone?: "quiet" | "trust" }) {
  const color = tone === "trust" ? "text-trust-gap" : "text-ink";
  return (
    <section className="border-t border-line pt-5">
      <p className="m-0 text-meta font-semibold uppercase text-muted">{label}</p>
      <p className={`m-0 mt-4 font-display text-[4.5rem] font-semibold leading-none ${color}`}>{value}</p>
    </section>
  );
}

function ReadyForTestList({ items }: { items: LearningItemView[] }) {
  const { t } = useI18n();
  return (
    <section className="border-t border-line pt-5">
      <div className="mb-4 flex items-baseline justify-between gap-4">
        <p className="m-0 text-meta font-semibold uppercase text-muted">{t("readyForTest")}</p>
        {!!items.length && <Link className="text-meta font-semibold text-ink underline decoration-line underline-offset-4" to="/trust-tests">{t("viewAll")}</Link>}
      </div>
      {items.length ? (
        <ul className="m-0 grid list-none gap-4 p-0">
          {items.slice(0, 4).map((item) => (
            <li key={item.id} className="border-b border-line pb-4 last:border-b-0">
              <p className="m-0 text-caption font-semibold text-ink">{item.title}</p>
              <p className="m-0 mt-1 text-meta text-muted">{compactMeta([item.source_type, item.status, item.internalization_level])}</p>
            </li>
          ))}
        </ul>
      ) : (
        <ZenBlank title={t("noTestCandidates")} body="Nothing is asking to be proven yet." compact />
      )}
    </section>
  );
}

function RecentActivityList({ items }: { items: DashboardView["recent_activity"] }) {
  const { t } = useI18n();
  return (
    <section className="border-t border-line pt-5">
      <p className="m-0 mb-4 text-meta font-semibold uppercase text-muted">{t("recentActivity")}</p>
      {items.length ? (
        <ol className="m-0 grid list-none gap-4 p-0">
          {items.slice(0, 4).map((item) => (
            <li key={item.id} className="grid gap-1">
              <p className="m-0 text-caption text-ink">{asText(item.summary)}</p>
              <time className="text-meta text-muted">{relativeTime(asText(item.timestamp))}</time>
            </li>
          ))}
        </ol>
      ) : (
        <ZenBlank title={t("noActivity")} body="The log will appear when learning state changes." compact />
      )}
    </section>
  );
}

function ZenBlank({ title, body, compact = false, className = "" }: { title: string; body: string; compact?: boolean; className?: string }) {
  return (
    <div className={`grid content-center ${compact ? "min-h-28" : "min-h-56"} ${className}`}>
      <p className="m-0 max-w-md font-display text-h2 text-ink">{title}</p>
      <p className="m-0 mt-2 max-w-md text-caption text-muted">{body}</p>
    </div>
  );
}

function visibleOpenLoops(counts: Record<string, number>) {
  return Object.entries(counts).filter(([, count]) => count > 0);
}

function loopLabel(key: string, language: Language) {
  return openLoopLabels[language][key] || key.replace(/_/g, " ");
}

function compactMeta(parts: Array<unknown>) {
  return parts.map(asText).filter(Boolean).join(" / ");
}

function formatActionType(value: string) {
  return value.replace(/_/g, " ");
}

function formatPriority(value: number) {
  return value > 0 ? `P${value}` : "P0";
}

function relativeTime(value: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.round(diffMs / 60000);
  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

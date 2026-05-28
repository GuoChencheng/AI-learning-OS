import type { ReactNode } from "react";
import { asText } from "../utils";

export type LearningItemRowItem = {
  id?: string;
  title?: unknown;
  topic?: unknown;
  text?: unknown;
  statement?: unknown;
  status?: unknown;
  epistemic_status?: unknown;
  record_intensity?: unknown;
  importance?: unknown;
  source_type?: unknown;
  internalization_level?: unknown;
  temporal_status?: unknown;
  next_action?: unknown;
};

type LearningItemRowProps = {
  item: LearningItemRowItem;
  metadataKeys?: Array<keyof LearningItemRowItem>;
  action?: ReactNode;
  onClick?: () => void;
};

const defaultMetadataKeys: Array<keyof LearningItemRowItem> = [
  "epistemic_status",
  "record_intensity",
  "importance",
  "source_type",
  "internalization_level",
  "temporal_status"
];

const attentionStatuses = new Set([
  "unverified",
  "needs_rederive",
  "needs_retest",
  "partially_correct",
  "misleading",
  "wrong",
  "failed",
  "active",
  "recurring"
]);

const urgentStatuses = new Set(["wrong", "failed", "misleading", "needs_retest"]);

export function LearningItemRow({
  item,
  metadataKeys = defaultMetadataKeys,
  action,
  onClick
}: LearningItemRowProps) {
  const title = rowTitle(item);
  const status = asText(item.status);
  const metadata = metadataKeys
    .map((key) => asText(item[key]))
    .filter(Boolean);
  const nextAction = asText(item.next_action);
  const interactive = Boolean(onClick);

  const content = (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <AttentionDot status={status} />
          <span className="truncate text-caption font-medium text-ink">{title || "Untitled learning item"}</span>
        </div>
        {!!metadata.length && (
          <p className="m-0 mt-1 truncate text-[0.625rem] font-semibold uppercase leading-tight tracking-normal text-subtle">
            {metadata.map(formatMeta).join(" / ")}
          </p>
        )}
        {nextAction && (
          <p className="m-0 mt-2 line-clamp-1 text-meta text-muted">{nextAction}</p>
        )}
      </div>
      {action && <div className="shrink-0 text-meta text-muted">{action}</div>}
    </>
  );

  if (interactive) {
    return (
      <button
        className="group flex min-h-0 w-full items-start justify-between gap-4 border-0 border-b border-line/60 bg-white px-0 py-3 text-left shadow-none hover:bg-white"
        onClick={onClick}
      >
        {content}
      </button>
    );
  }

  return (
    <article className="flex min-w-0 items-start justify-between gap-4 border-b border-line/60 bg-white py-3">
      {content}
    </article>
  );
}

function AttentionDot({ status }: { status: string }) {
  if (!attentionStatuses.has(status)) return null;
  const tone = urgentStatuses.has(status) ? "bg-overdue" : "bg-trust-gap";
  return <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${tone}`} aria-label={`${formatMeta(status)} needs attention`} />;
}

function rowTitle(item: LearningItemRowItem) {
  return asText(item.title || item.topic || item.text || item.statement || item.id);
}

function formatMeta(value: string) {
  return value.replace(/_/g, " ");
}

import { asText, statusTone } from "../utils";

export function StatusBadge({ value }: { value: unknown }) {
  const tone = statusTone(value);
  return <span className={`badge badge-${tone}`}>{asText(value) || "none"}</span>;
}

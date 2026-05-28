export function asText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export function listFromText(value: string): string[] {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function textFromList(value: unknown): string {
  return Array.isArray(value) ? value.join("\n") : asText(value);
}

export function statusTone(value: unknown): string {
  const text = asText(value);
  if (["wrong", "misleading", "failed", "needs_rederive", "needs_retest", "heavy", "A0"].includes(text)) return "danger";
  if (["unverified", "partial", "partially_correct", "planned", "medium", "A1", "A2"].includes(text)) return "warn";
  if (["verified", "trusted", "passed", "read", "A3", "A4"].includes(text)) return "good";
  if (text.startsWith("A_no_ai")) return "strong";
  if (text.startsWith("B_")) return "info";
  return "neutral";
}

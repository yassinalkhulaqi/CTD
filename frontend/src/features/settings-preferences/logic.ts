import type { PreferenceSchemaField } from "./types";

export function groupFields(
  fields: PreferenceSchemaField[],
): Record<string, PreferenceSchemaField[]> {
  const groups: Record<string, PreferenceSchemaField[]> = {};
  for (const field of fields) {
    const group = field.key.split(".")[0] ?? "general";
    groups[group] = [...(groups[group] ?? []), field];
  }
  return groups;
}

export function isDirtyValues(
  current: Record<string, unknown>,
  draft: Record<string, unknown>,
): boolean {
  return Object.keys(draft).some(
    (k) => JSON.stringify(current[k]) !== JSON.stringify(draft[k]),
  );
}

export function toNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  if (
    typeof value === "string" &&
    value.trim() !== "" &&
    !Number.isNaN(Number(value))
  )
    return Number(value);
  return fallback;
}

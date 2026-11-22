/**
 * Pure helpers shared by the integrations components.
 *
 * Keeping these separate from React makes the validation, formatting and
 * aggregation rules easy to exercise with unit tests.
 */

import {
  ALL_EVENTS,
  EVENT_LABELS,
  KIND_LABELS,
  type Adapter,
  type BadgeTone,
  type DeliveryStatus,
  type IntegrationDraft,
  type IntegrationKind,
  type IntegrationStats,
} from "./types";

/** Validate the shape of an integration endpoint URL in the browser. */
export function isValidEndpointUrl(value: string): boolean {
  const candidate = value.trim();
  if (!candidate) return false;
  try {
    const parsed = new URL(candidate);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password &&
      !parsed.hash
    );
  } catch {
    return false;
  }
}

/** Return a masked preview of a secret that never exposes its middle. */
export function maskDisplay(value: string): string {
  if (!value) return "";
  if (value.length <= 4) return "•".repeat(value.length);
  const width = Math.min(8, value.length - 4);
  return `${value.slice(0, 2)}${"•".repeat(width)}${value.slice(-2)}`;
}

/** Normalise and de-duplicate a list of event names. */
export function normaliseEvents(events: readonly string[]): string[] {
  const seen = new Set<string>();
  for (const raw of events) {
    const event = raw.trim().toLowerCase();
    if (event && ALL_EVENTS.includes(event)) seen.add(event);
  }
  return [...seen];
}

/** Return the human readable label of an event. */
export function eventLabel(event: string): string {
  return EVENT_LABELS[event] ?? event;
}

/** Return the human readable label of a transport kind. */
export function kindLabel(kind: IntegrationKind): string {
  return KIND_LABELS[kind] ?? kind;
}

/** Return the semantic badge tone for a delivery status. */
export function deliveryTone(status: DeliveryStatus): BadgeTone {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  return "warning";
}

/** Format an ISO timestamp for display, or return a placeholder. */
export function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** Format a ratio as a whole percentage. */
export function percentage(ratio: number): string {
  return `${Math.round(Math.min(1, Math.max(0, ratio)) * 100)}%`;
}

/** Format a retry delay in a compact, human readable form. */
export function retryLabel(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)}m`;
}

/** Return sorted source/target pairs from an adapter mapping. */
export function eventMapEntries(
  map: Record<string, string>,
): Array<[string, string]> {
  return Object.entries(map).sort(([left], [right]) =>
    left.localeCompare(right),
  );
}

/** Return the busiest events from the statistics payload. */
export function topEvents(
  stats: IntegrationStats,
  limit = 3,
): Array<[string, number]> {
  return Object.entries(stats.by_event)
    .sort(
      (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
    )
    .slice(0, limit);
}

/** Return a short prose summary of the delivery statistics. */
export function summariseStats(stats: IntegrationStats): string {
  if (stats.total_deliveries === 0) return "No deliveries recorded yet";
  return `${stats.successful_deliveries} of ${stats.total_deliveries} deliveries succeeded`;
}

/** Validate an integration form draft and return field errors. */
export function validateDraft(
  draft: IntegrationDraft,
): Partial<Record<"name" | "endpoint_url" | "events" | "secret", string>> {
  const errors: Partial<
    Record<"name" | "endpoint_url" | "events" | "secret", string>
  > = {};
  if (!draft.name.trim()) errors.name = "Give the integration a name";
  else if (draft.name.trim().length > 120)
    errors.name = "Keep the name under 120 characters";
  if (!isValidEndpointUrl(draft.endpoint_url)) {
    errors.endpoint_url = "Use a valid http or https URL without credentials";
  }
  if (draft.events.length === 0) errors.events = "Select at least one event";
  if (draft.secret && draft.secret.length < 8) {
    errors.secret = "Secrets need at least 8 characters";
  }
  return errors;
}

/** Return whether an adapter maps any events. */
export function hasMappings(adapter: Adapter): boolean {
  return adapter.mapping_count > 0;
}

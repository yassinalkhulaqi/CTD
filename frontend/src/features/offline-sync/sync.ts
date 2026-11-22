/**
 * Pure helpers for the offline sync screen.
 *
 * These functions contain no React or network concerns so the queue, conflict
 * and connectivity rules can be tested directly.
 */

import { formatPercent, formatRelativeTime } from "../../lib/utils";
import type {
  ConnectivityCopy,
  ConflictStrategy,
  MergePreview,
  MutationOperation,
  MutationStatus,
  Payload,
  PendingMutation,
  StatusTone,
  SyncHealth,
  SyncStatus,
} from "./types";

/** Strategies offered by the conflict resolution dialog. */
export const STRATEGY_OPTIONS: ReadonlyArray<{
  value: ConflictStrategy;
  label: string;
  hint: string;
}> = [
  {
    value: "local_wins",
    label: "Local wins",
    hint: "Keep every offline edit and discard the server changes.",
  },
  {
    value: "remote_wins",
    label: "Remote wins",
    hint: "Accept the server version and drop conflicting local edits.",
  },
  {
    value: "merge",
    label: "Merge fields",
    hint: "Combine both sides field by field and flag contested values.",
  },
];

/** Status filters shown above the queue inspector. */
export const STATUS_FILTERS: ReadonlyArray<{
  value: MutationStatus | "all";
  label: string;
}> = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "conflict", label: "Conflicts" },
  { value: "synced", label: "Synced" },
];

const UNDEFINED_MARKER = "__offline_sync_undefined__";

/** Return whether a string names a supported conflict strategy. */
export function isValidStrategy(value: string): value is ConflictStrategy {
  return STRATEGY_OPTIONS.some((option) => option.value === value);
}

/** Map a mutation status onto a design system tone. */
export function statusTone(status: MutationStatus): StatusTone {
  if (status === "synced") return "success";
  if (status === "conflict") return "danger";
  return "warning";
}

/** Return the human readable label of a mutation status. */
export function statusLabel(status: MutationStatus): string {
  if (status === "synced") return "Synced";
  if (status === "conflict") return "Conflict";
  return "Pending";
}

/** Map an operation onto a design system tone. */
export function operationTone(operation: MutationOperation): StatusTone {
  if (operation === "create") return "success";
  if (operation === "delete") return "danger";
  return "info";
}

/** Return the past-tense label of an operation. */
export function operationLabel(operation: MutationOperation): string {
  if (operation === "create") return "Created";
  if (operation === "delete") return "Deleted";
  return "Updated";
}

/** Map a health label onto a design system tone. */
export function healthTone(health: SyncHealth): StatusTone {
  if (health === "healthy") return "success";
  if (health === "attention") return "danger";
  if (health === "syncing") return "info";
  return "neutral";
}

/** Return a friendlier phrase for a health label. */
export function healthLabel(health: SyncHealth): string {
  if (health === "healthy") return "Everything is up to date";
  if (health === "attention") return "Conflicts need attention";
  if (health === "syncing") return "Changes are waiting to sync";
  return "Nothing queued yet";
}

/** Build the banner copy for the current connectivity state. */
export function connectivityCopy(
  online: boolean,
  pending: number,
): ConnectivityCopy {
  if (!online) {
    return {
      title: "You are offline",
      detail:
        pending > 0
          ? `${pending} change${pending === 1 ? "" : "s"} will sync when you reconnect.`
          : "New edits will be queued locally until you reconnect.",
      tone: "warning",
    };
  }
  if (pending > 0) {
    return {
      title: "Back online",
      detail: `${pending} queued change${pending === 1 ? "" : "s"} ready to sync.`,
      tone: "info",
    };
  }
  return {
    title: "Connected",
    detail: "Your workspace is in sync with the server.",
    tone: "success",
  };
}

/** Return an accessible description for a mutation row. */
export function describeMutation(mutation: PendingMutation): string {
  return `${statusLabel(mutation.status)} ${mutation.operation} for ${mutation.entity_label}, base version ${mutation.base_version}, ${mutation.attempts} attempts`;
}

/** Produce a short single line preview of a JSON payload. */
export function payloadPreview(payload: Payload, maxLength = 88): string {
  const text = JSON.stringify(payload);
  if (!text) return "No payload";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

/** Format a timestamp relative to now, falling back to a dash. */
export function formatAge(iso: string, now: Date = new Date()): string {
  return formatRelativeTime(iso, now);
}

/** Format an attempt count with correct pluralisation. */
export function formatAttempts(attempts: number): string {
  if (attempts === 0) return "Not attempted";
  return `${attempts} attempt${attempts === 1 ? "" : "s"}`;
}

/** Group mutations by their lifecycle status. */
export function groupMutations(
  items: PendingMutation[],
): Record<MutationStatus, PendingMutation[]> {
  const grouped: Record<MutationStatus, PendingMutation[]> = {
    pending: [],
    synced: [],
    conflict: [],
  };
  for (const item of items) grouped[item.status].push(item);
  return grouped;
}

/** Return only the mutations paused by a version conflict. */
export function conflictedMutations(items: PendingMutation[]): PendingMutation[] {
  return items.filter((item) => item.status === "conflict");
}

/** Sort mutations by creation time and identifier, oldest first. */
export function sortMutations(
  items: PendingMutation[],
  newestFirst = false,
): PendingMutation[] {
  const sorted = [...items].sort((left, right) => {
    const byTime = left.created_at.localeCompare(right.created_at);
    return byTime === 0 ? left.id.localeCompare(right.id) : byTime;
  });
  return newestFirst ? sorted.reverse() : sorted;
}

/** Infer server versions from the highest base version seen per entity. */
export function buildCurrentVersions(items: PendingMutation[]): Record<string, number> {
  const versions: Record<string, number> = {};
  for (const item of items) {
    versions[item.entity] = Math.max(versions[item.entity] ?? 0, item.base_version);
  }
  return versions;
}

/** Count mutations by status. */
export function summariseQueue(
  items: PendingMutation[],
): Record<MutationStatus, number> & { total: number } {
  const grouped = groupMutations(items);
  return {
    pending: grouped.pending.length,
    synced: grouped.synced.length,
    conflict: grouped.conflict.length,
    total: items.length,
  };
}

/** Format the completion rate shown beneath the progress bar. */
export function completionText(status: SyncStatus | null): string {
  if (!status || status.total === 0) return "No changes recorded";
  return `${formatPercent(status.completion_rate, 0)} complete`;
}

/** Return the copy used by the manual sync button. */
export function syncButtonLabel(
  online: boolean,
  busy: boolean,
  pending: number,
): string {
  if (busy) return "Syncing…";
  if (!online) return "Offline";
  if (pending === 0) return "Sync now";
  return `Sync ${pending} change${pending === 1 ? "" : "s"}`;
}

function stable(value: unknown): string {
  if (value === undefined) return UNDEFINED_MARKER;
  try {
    return JSON.stringify(value) ?? "null";
  } catch {
    return String(value);
  }
}

function sameValue(left: unknown, right: unknown): boolean {
  return stable(left) === stable(right);
}

/** Parse a JSON object entered into the dialog's payload editors. */
export function parseJsonObject(
  raw: string,
): { ok: true; value: Payload } | { ok: false; error: string } {
  const trimmed = raw.trim();
  if (!trimmed) return { ok: true, value: {} };
  let decoded: unknown;
  try {
    decoded = JSON.parse(trimmed);
  } catch {
    return { ok: false, error: "Enter a valid JSON object." };
  }
  if (typeof decoded !== "object" || decoded === null || Array.isArray(decoded)) {
    return { ok: false, error: "The payload must be a JSON object." };
  }
  return { ok: true, value: decoded as Payload };
}

/** Preview the outcome of a merge strategy without calling the API. */
export function mergePreview(
  base: Payload,
  local: Payload,
  remote: Payload,
  strategy: ConflictStrategy,
): MergePreview {
  const fields = Array.from(new Set([...Object.keys(base), ...Object.keys(local), ...Object.keys(remote)])).sort();

  if (strategy === "local_wins") {
    return { payload: { ...remote, ...local }, contested: [], fields };
  }
  if (strategy === "remote_wins") {
    return { payload: { ...local, ...remote }, contested: [], fields };
  }

  const payload: Payload = {};
  const contested: string[] = [];
  for (const field of fields) {
    const inLocal = Object.prototype.hasOwnProperty.call(local, field);
    const inRemote = Object.prototype.hasOwnProperty.call(remote, field);
    const inBase = Object.prototype.hasOwnProperty.call(base, field);
    const localValue = local[field];
    const remoteValue = remote[field];
    const baseValue = base[field];

    let chosen: unknown;
    if (sameValue(localValue, remoteValue)) {
      chosen = localValue;
    } else if (!inLocal || (inBase && sameValue(localValue, baseValue))) {
      chosen = remoteValue;
    } else if (!inRemote || (inBase && sameValue(remoteValue, baseValue))) {
      chosen = localValue;
    } else {
      chosen = localValue;
      contested.push(field);
    }

    if ((inLocal || inRemote) && chosen !== undefined) payload[field] = chosen;
  }
  return { payload, contested, fields };
}

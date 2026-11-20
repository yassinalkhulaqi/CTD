/** Pure helpers for filters, preferences, digest grouping and toasts. */

import type {
  Channel,
  DigestGroup,
  DigestEntry,
  DigestPreviewPayload,
  Notification,
  NotificationFilters,
  NotificationKind,
  Preference,
  PreferenceInput,
  PreferenceKey,
  Severity,
  ToastItem,
} from "./types";

/** Urgency of each severity, from least to most important. */
export const SEVERITY_RANK: Record<Severity, number> = {
  info: 0,
  warning: 1,
  critical: 2,
};

/** Severities ordered from most to least urgent. */
export const SEVERITIES: Severity[] = ["critical", "warning", "info"];

/** Channels rendered in the preference panel. */
export const CHANNELS: Channel[] = ["in_app", "email", "webhook"];

/** Concrete kinds rendered in the preference panel. */
export const KINDS: NotificationKind[] = [
  "solve",
  "challenge",
  "team",
  "security",
  "system",
];

/** Human readable labels for notification kinds. */
export const KIND_LABELS: Record<NotificationKind, string> = {
  solve: "Solves",
  challenge: "Challenges",
  team: "Team",
  system: "System",
  security: "Security",
  "*": "All events",
};

/** Human readable labels for delivery channels. */
export const CHANNEL_LABELS: Record<Channel, string> = {
  in_app: "In app",
  email: "Email",
  webhook: "Webhook",
};

/**
 * Sort notifications by urgency, then by descending creation time.
 *
 * @param items - The notifications to sort.
 * @returns A new sorted array.
 */
export function sortNotifications(items: Notification[]): Notification[] {
  return [...items].sort((left, right) => {
    const rank = SEVERITY_RANK[right.severity] - SEVERITY_RANK[left.severity];
    if (rank !== 0) return rank;
    const time = Date.parse(right.created_at) - Date.parse(left.created_at);
    if (time !== 0) return time;
    return left.id.localeCompare(right.id);
  });
}

/**
 * Return notifications matching every active filter.
 *
 * @param items - The source notifications.
 * @param filters - The active filters.
 * @returns The matching notifications in display order.
 */
export function filterNotifications(
  items: Notification[],
  filters: NotificationFilters,
): Notification[] {
  const needle = filters.search.trim().toLowerCase();
  const matching = items.filter((item) => {
    if (filters.kind !== "all" && item.kind !== filters.kind) return false;
    if (filters.severity !== "all" && item.severity !== filters.severity)
      return false;
    if (filters.unreadOnly && !item.is_unread) return false;
    if (
      needle &&
      !item.title.toLowerCase().includes(needle) &&
      !item.body.toLowerCase().includes(needle)
    )
      return false;
    return true;
  });
  return sortNotifications(matching);
}

/**
 * Count unread notifications.
 *
 * @param items - The notifications to inspect.
 * @returns The unread count.
 */
export function unreadCount(items: Notification[]): number {
  return items.filter((item) => item.is_unread).length;
}

/**
 * Group notifications by kind for the filter chips.
 *
 * @param items - The notifications to group.
 * @returns Kinds paired with their counts, in stable order.
 */
export function countByKind(
  items: Notification[],
): Array<{ kind: NotificationKind; count: number }> {
  return KINDS.map((kind) => ({
    kind,
    count: items.filter((item) => item.kind === kind).length,
  })).filter((entry) => entry.count > 0);
}

/**
 * Map a severity to a design-system badge tone.
 *
 * @param severity - The notification severity.
 * @returns The badge tone.
 */
export function severityTone(
  severity: Severity,
): "info" | "warning" | "danger" {
  if (severity === "critical") return "danger";
  if (severity === "warning") return "warning";
  return "info";
}

/**
 * Map a severity to a CSS module class suffix.
 *
 * @param severity - The notification severity.
 * @returns The class suffix.
 */
export function severityClass(severity: Severity): string {
  return `severity-${severity}`;
}

/**
 * Coerce an arbitrary hour into the 0–23 range.
 *
 * @param hour - The hour to normalise.
 * @returns The normalised hour.
 */
export function normaliseHour(hour: number): number {
  if (!Number.isFinite(hour)) return 0;
  return Math.min(23, Math.max(0, Math.trunc(hour)));
}

/**
 * Format an hour as a two-digit wall clock value.
 *
 * @param hour - The hour to format.
 * @returns A string such as `07`.
 */
export function formatHour(hour: number): string {
  return String(normaliseHour(hour)).padStart(2, "0");
}

/**
 * Decide whether an hour falls inside a quiet window.
 *
 * Windows that wrap past midnight are supported. Equal start and end hours
 * mean the feature is disabled.
 *
 * @param start - First suppressed hour.
 * @param end - First hour after the suppressed window.
 * @param hour - The hour to test.
 * @returns Whether delivery should be held back.
 */
export function isWithinQuietHours(
  start: number,
  end: number,
  hour: number,
): boolean {
  const from = normaliseHour(start);
  const to = normaliseHour(end);
  const current = normaliseHour(hour);
  if (from === to) return false;
  if (from < to) return current >= from && current < to;
  return current >= from || current < to;
}

/**
 * Resolve the effective enabled state of a channel/kind pair.
 *
 * Exact preferences take priority over channel-wide wildcard rules; when
 * nothing is stored delivery is enabled by default.
 *
 * @param preferences - The stored preference rows.
 * @param channel - The delivery channel.
 * @param kind - The event kind.
 * @returns Whether the pair is enabled.
 */
export function isPreferenceEnabled(
  preferences: Preference[],
  channel: Channel,
  kind: NotificationKind,
): boolean {
  const exact = preferences.find(
    (item) => item.channel === channel && item.kind === kind,
  );
  if (exact) return exact.enabled;
  const wildcard = preferences.find(
    (item) => item.channel === channel && item.kind === "*",
  );
  return wildcard ? wildcard.enabled : true;
}

/**
 * Return preferences with one key toggled, inserting a row when needed.
 *
 * @param preferences - The stored preference rows.
 * @param channel - The delivery channel.
 * @param kind - The event kind.
 * @param enabled - The new enabled state.
 * @returns A new preference array.
 */
export function togglePreference(
  preferences: Preference[],
  channel: Channel,
  kind: NotificationKind,
  enabled: boolean,
): PreferenceInput[] {
  return upsertPreferenceInput(preferences, { channel, kind }, { enabled });
}

/**
 * Return preferences with one quiet window changed.
 *
 * @param preferences - The stored preference rows.
 * @param channel - The delivery channel.
 * @param kind - The event kind.
 * @param start - New first suppressed hour.
 * @param end - New first unsuppressed hour.
 * @returns A new preference payload array.
 */
export function setQuietHours(
  preferences: Preference[],
  channel: Channel,
  kind: NotificationKind,
  start: number,
  end: number,
): PreferenceInput[] {
  return upsertPreferenceInput(
    preferences,
    { channel, kind },
    {
      quiet_start_hour: normaliseHour(start),
      quiet_end_hour: normaliseHour(end),
    },
  );
}

/**
 * Merge a partial change into the preference matching a key.
 *
 * @param preferences - The stored preference rows.
 * @param key - The channel and kind to modify.
 * @param patch - The fields to change.
 * @returns Payloads for every preference row, with the change applied.
 */
export function upsertPreferenceInput(
  preferences: Preference[],
  key: PreferenceKey,
  patch: Partial<PreferenceInput>,
): PreferenceInput[] {
  const recipientId = preferences[0]?.recipient_id ?? "";
  const rows = new Map<string, PreferenceInput>();
  for (const item of preferences) {
    rows.set(`${item.channel}:${item.kind}`, {
      recipient_id: item.recipient_id,
      channel: item.channel,
      kind: item.kind,
      enabled: item.enabled,
      quiet_start_hour: item.quiet_start_hour,
      quiet_end_hour: item.quiet_end_hour,
    });
  }
  const targetKey = `${key.channel}:${key.kind}`;
  rows.set(targetKey, {
    recipient_id: recipientId,
    channel: key.channel,
    kind: key.kind,
    enabled: true,
    quiet_start_hour: 0,
    quiet_end_hour: 0,
    ...rows.get(targetKey),
    ...patch,
  });
  return [...rows.values()];
}

/**
 * Build a toast from a delivered notification.
 *
 * @param notification - The delivered notification.
 * @param ttl - Lifetime in milliseconds.
 * @param now - Current timestamp in milliseconds.
 * @returns The new toast.
 */
export function makeToast(
  notification: Notification,
  ttl = 6000,
  now = Date.now(),
): ToastItem {
  return {
    id: `toast-${notification.id}`,
    notification,
    tone: notification.severity,
    ttl,
    createdAt: now,
  };
}

/**
 * Decide whether a toast has outlived its lifetime.
 *
 * @param toast - The toast to inspect.
 * @param now - Current timestamp in milliseconds.
 * @returns Whether the toast should be dismissed.
 */
export function shouldAutoDismiss(toast: ToastItem, now: number): boolean {
  if (toast.ttl <= 0) return false;
  return now - toast.createdAt >= toast.ttl;
}

/**
 * Keep only the most recent toasts, up to ``max``.
 *
 * @param toasts - The current queue.
 * @param max - Maximum number of visible toasts.
 * @returns The trimmed queue.
 */
export function trimToasts(toasts: ToastItem[], max = 4): ToastItem[] {
  if (max <= 0) return [];
  return toasts.slice(-max);
}

/**
 * Remove one toast by identifier.
 *
 * @param toasts - The current queue.
 * @param id - The toast identifier.
 * @returns The filtered queue.
 */
export function dismissToast(toasts: ToastItem[], id: string): ToastItem[] {
  return toasts.filter((toast) => toast.id !== id);
}

/**
 * Summarise the groups of a digest preview.
 *
 * @param preview - The digest preview.
 * @returns A one-line summary.
 */
export function digestHeadline(preview: DigestPreviewPayload | null): string {
  if (!preview || preview.total === 0) return "No notifications in this period";
  const parts = preview.groups.map((group) => `${group.count} ${group.kind}`);
  return `${preview.total} notification${preview.total === 1 ? "" : "s"}: ${parts.join(", ")}`;
}

/**
 * Group digest entries by severity for compact display.
 *
 * @param entries - The digest entries.
 * @returns Severity labels paired with counts.
 */
export function countBySeverity(
  entries: DigestEntry[],
): Array<{ severity: Severity; count: number }> {
  return SEVERITIES.map((severity) => ({
    severity,
    count: entries.filter((entry) => entry.severity === severity).length,
  })).filter((entry) => entry.count > 0);
}

/**
 * Summarise the number of digest groups per kind.
 *
 * @param groups - The digest groups.
 * @returns The total number of grouped messages.
 */
export function digestGroupTotal(groups: DigestGroup[]): number {
  return groups.reduce((sum, group) => sum + group.count, 0);
}

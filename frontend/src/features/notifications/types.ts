/** Domain types and view models for the notification centre. */

export type Channel = "in_app" | "email" | "webhook";

export type NotificationKind =
  "solve" | "challenge" | "team" | "system" | "security" | "*";

export type Severity = "info" | "warning" | "critical";

export type DigestPeriod = "hourly" | "daily" | "weekly";

/** A notification returned by the API. */
export interface Notification {
  id: string;
  recipient_id: string;
  channel: Channel;
  kind: NotificationKind;
  title: string;
  body: string;
  severity: Severity;
  read_at: string | null;
  created_at: string;
  action_url: string;
  is_read: boolean;
  is_unread: boolean;
  severity_rank: number;
  label: string;
  age_seconds: number;
}

/** A filtered listing of notifications. */
export interface NotificationPage {
  items: Notification[];
  total: number;
  unread: number;
  limit: number;
  offset: number;
}

/** Explanation of whether a newly created message was delivered. */
export interface DeliveryDecision {
  channel: Channel;
  delivered: boolean;
  reason: string;
  suppressed_until_hour: number | null;
}

/** Result of emitting a notification. */
export interface CreateResult {
  notification: Notification;
  decision: DeliveryDecision;
  delivered: boolean;
}

/** Delivery settings for one channel and kind. */
export interface Preference {
  recipient_id: string;
  channel: Channel;
  kind: NotificationKind;
  enabled: boolean;
  quiet_start_hour: number;
  quiet_end_hour: number;
  quiet_hours: string;
}

/** Complete preference matrix of a recipient. */
export interface PreferenceList {
  recipient_id: string;
  preferences: Preference[];
}

/** A notification condensed into a digest. */
export interface DigestEntry {
  notification_id: string;
  kind: NotificationKind;
  severity: Severity;
  title: string;
  body: string;
  created_at: string;
  action_url: string;
}

/** Digest entries sharing a kind and severity. */
export interface DigestGroup {
  kind: NotificationKind;
  severity: Severity;
  count: number;
  headline: string;
  entries: DigestEntry[];
}

/** A persisted digest. */
export interface Digest {
  id: string;
  recipient_id: string;
  period: DigestPeriod;
  entries: DigestEntry[];
  groups: DigestGroup[];
  total: number;
  sent_at: string | null;
  is_sent: boolean;
  markdown: string;
}

/** An unsaved digest preview. */
export interface DigestPreviewPayload {
  recipient_id: string;
  period: DigestPeriod;
  total: number;
  groups: DigestGroup[];
  entries: DigestEntry[];
  markdown: string;
  generated_at: string;
}

/** Aggregated counters for the notification centre header. */
export interface NotificationStats {
  total: number;
  read: number;
  unread: number;
  critical_unread: number;
  read_rate: number;
  by_channel: Record<string, number>;
  by_kind: Record<string, number>;
  by_severity: Record<string, number>;
}

/** Result of a mark-all-read request. */
export interface MarkReadResult {
  notification_id: string | null;
  modified: number;
  unread: number;
}

/** Result of a retention prune. */
export interface PruneResult {
  removed: number;
  max_age_days: number;
  keep_unread: boolean;
}

/** Notification kinds selectable through the UI. */
export type KindFilter = NotificationKind | "all";

/** Severities selectable through the UI. */
export type SeverityFilter = Severity | "all";

/** Filters applied to the centre's notification list. */
export interface NotificationFilters {
  kind: KindFilter;
  severity: SeverityFilter;
  unreadOnly: boolean;
  search: string;
}

/** A toast surfaced from a notification. */
export interface ToastItem {
  id: string;
  notification: Notification;
  tone: Severity;
  ttl: number;
  createdAt: number;
}

/** Payload used to emit a notification. */
export interface CreateNotificationInput {
  recipient_id: string;
  channel: Channel;
  kind: NotificationKind;
  title: string;
  body: string;
  variables?: Record<string, unknown>;
  severity?: Severity;
  action_url?: string;
}

/** Payload used to change one preference row. */
export interface PreferenceInput {
  recipient_id: string;
  channel: Channel;
  kind: NotificationKind;
  enabled: boolean;
  quiet_start_hour: number;
  quiet_end_hour: number;
}

/** A preference key used for lookups. */
export interface PreferenceKey {
  channel: Channel;
  kind: NotificationKind;
}

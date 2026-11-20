/** Typed API adapter for the notification centre. */

import { buildQuery, get, post, put } from "../../api/client";
import type {
  CreateNotificationInput,
  CreateResult,
  Digest,
  DigestPeriod,
  DigestPreviewPayload,
  MarkReadResult,
  Notification,
  NotificationPage,
  NotificationStats,
  Preference,
  PreferenceInput,
  PreferenceList,
  PruneResult,
  Severity,
} from "./types";

/** Base path of the notification API. */
export const NOTIFICATIONS_PATH = "/api/notifications";

/** Query parameters accepted by the listing endpoint. */
export interface ListNotificationsParams {
  recipientId?: string;
  channel?: string;
  kind?: string;
  severity?: Severity;
  unreadOnly?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

/**
 * Fetch a filtered notification page.
 *
 * @param params - Optional filters and pagination.
 * @returns The page of notifications.
 */
export function listNotifications(
  params: ListNotificationsParams = {},
): Promise<NotificationPage> {
  const query = buildQuery({
    recipient_id: params.recipientId,
    channel: params.channel,
    kind: params.kind,
    severity: params.severity,
    unread_only: params.unreadOnly,
    search: params.search,
    limit: params.limit,
    offset: params.offset,
  });
  return get<NotificationPage>(`${NOTIFICATIONS_PATH}${query}`);
}

/**
 * Emit a notification.
 *
 * @param input - The notification payload.
 * @returns The stored notification and its delivery decision.
 */
export function createNotification(
  input: CreateNotificationInput,
): Promise<CreateResult> {
  return post<CreateResult>(NOTIFICATIONS_PATH, input);
}

/**
 * Acknowledge one notification.
 *
 * @param id - The notification identifier.
 * @returns The updated notification.
 */
export function markNotificationRead(id: string): Promise<Notification> {
  return post<Notification>(
    `${NOTIFICATIONS_PATH}/${encodeURIComponent(id)}/read`,
  );
}

/**
 * Acknowledge every notification of a recipient.
 *
 * @param recipientId - The recipient identifier.
 * @returns The number of messages changed.
 */
export function markAllRead(recipientId: string): Promise<MarkReadResult> {
  return post<MarkReadResult>(`${NOTIFICATIONS_PATH}/read-all`, {
    recipient_id: recipientId,
  });
}

/**
 * Fetch the effective preference matrix of a recipient.
 *
 * @param recipientId - The recipient identifier.
 * @returns The preference list.
 */
export function listPreferences(recipientId: string): Promise<PreferenceList> {
  const query = buildQuery({ recipient_id: recipientId });
  return get<PreferenceList>(`${NOTIFICATIONS_PATH}/preferences${query}`);
}

/**
 * Create or update one preference row.
 *
 * @param input - The preference payload.
 * @returns The stored preference.
 */
export function upsertPreference(input: PreferenceInput): Promise<Preference> {
  return put<Preference>(`${NOTIFICATIONS_PATH}/preferences`, input);
}

/**
 * Fetch an unsaved digest preview.
 *
 * @param recipientId - The recipient identifier.
 * @param period - The digest period.
 * @returns The preview payload.
 */
export function getDigestPreview(
  recipientId: string,
  period: DigestPeriod,
): Promise<DigestPreviewPayload> {
  const query = buildQuery({ recipient_id: recipientId, period });
  return get<DigestPreviewPayload>(`${NOTIFICATIONS_PATH}/digest${query}`);
}

/**
 * Generate and persist a digest.
 *
 * @param recipientId - The recipient identifier.
 * @param period - The digest period.
 * @returns The stored digest.
 */
export function buildDigest(
  recipientId: string,
  period: DigestPeriod,
): Promise<Digest> {
  const query = buildQuery({ recipient_id: recipientId, period });
  return post<Digest>(`${NOTIFICATIONS_PATH}/digest${query}`);
}

/**
 * Mark a stored digest as dispatched.
 *
 * @param digestId - The digest identifier.
 * @returns The updated digest.
 */
export function sendDigest(digestId: string): Promise<Digest> {
  return post<Digest>(`${NOTIFICATIONS_PATH}/digest/send`, {
    digest_id: digestId,
  });
}

/**
 * Fetch notification counters.
 *
 * @param recipientId - Optional recipient filter.
 * @returns The aggregated stats.
 */
export function getStats(recipientId?: string): Promise<NotificationStats> {
  const query = buildQuery({ recipient_id: recipientId });
  return get<NotificationStats>(`${NOTIFICATIONS_PATH}/stats${query}`);
}

/**
 * Prune notifications older than the retention window.
 *
 * @param maxAgeDays - Maximum age in days.
 * @param keepUnread - Whether unread messages are retained.
 * @returns The prune summary.
 */
export function pruneNotifications(
  maxAgeDays = 30,
  keepUnread = true,
): Promise<PruneResult> {
  return post<PruneResult>(`${NOTIFICATIONS_PATH}/prune`, {
    max_age_days: maxAgeDays,
    keep_unread: keepUnread,
  });
}

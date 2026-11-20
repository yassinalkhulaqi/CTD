/** Data loading and local state hooks for the notification centre. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toApiError } from "../../api/client";
import * as api from "./api";
import {
  dismissToast,
  filterNotifications,
  makeToast,
  shouldAutoDismiss,
  trimToasts,
  unreadCount,
} from "./logic";
import type {
  DigestPeriod,
  Notification,
  NotificationFilters,
  NotificationStats,
  Preference,
  PreferenceInput,
  ToastItem,
} from "./types";

const EMPTY_STATS: NotificationStats = {
  total: 0,
  read: 0,
  unread: 0,
  critical_unread: 0,
  read_rate: 0,
  by_channel: {},
  by_kind: {},
  by_severity: {},
};

/** State returned by {@link useNotificationCentre}. */
export interface NotificationCentreState {
  /** Notifications returned by the API. */
  notifications: Notification[];
  /** Notification filters controlled by the UI. */
  filters: NotificationFilters;
  /** Visible notifications after filtering. */
  visible: Notification[];
  /** Unread count of the raw notification list. */
  unread: number;
  /** Effective preference matrix. */
  preferences: Preference[];
  /** Aggregated counters. */
  stats: NotificationStats;
  /** Current digest period. */
  period: DigestPeriod;
  /** Whether the initial request is in flight. */
  loading: boolean;
  /** Whether a mutation is in flight. */
  saving: boolean;
  /** Last error message, if any. */
  error: string | null;
  /** Update one filter field. */
  setFilter: <K extends keyof NotificationFilters>(
    key: K,
    value: NotificationFilters[K],
  ) => void;
  /** Change the digest period. */
  setPeriod: (period: DigestPeriod) => void;
  /** Reload all data from the API. */
  reload: () => Promise<void>;
  /** Acknowledge one notification with an optimistic update. */
  markRead: (id: string) => Promise<Notification | null>;
  /** Acknowledge every notification with an optimistic update. */
  markAllRead: () => Promise<number>;
  /** Persist one preference with an optimistic update. */
  savePreference: (input: PreferenceInput) => Promise<Preference | null>;
}

/**
 * Load and manage the data backing the notification centre.
 *
 * @param recipientId - The recipient whose notifications are shown.
 * @returns The centre state and actions.
 */
export function useNotificationCentre(
  recipientId: string,
): NotificationCentreState {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [stats, setStats] = useState<NotificationStats>(EMPTY_STATS);
  const [filters, setFilters] = useState<NotificationFilters>({
    kind: "all",
    severity: "all",
    unreadOnly: false,
    search: "",
  });
  const [period, setPeriod] = useState<DigestPeriod>("daily");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [page, preferenceList, summary] = await Promise.all([
        api.listNotifications({ recipientId, limit: 200 }),
        api.listPreferences(recipientId),
        api.getStats(recipientId),
      ]);
      if (!mounted.current) return;
      setNotifications(page.items);
      setPreferences(preferenceList.preferences);
      setStats(summary);
    } catch (cause) {
      if (mounted.current) setError(toApiError(cause).message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const setFilter = useCallback(
    <K extends keyof NotificationFilters>(
      key: K,
      value: NotificationFilters[K],
    ) => {
      setFilters((current) => ({ ...current, [key]: value }));
    },
    [],
  );

  const visible = useMemo(
    () => filterNotifications(notifications, filters),
    [notifications, filters],
  );
  const unread = useMemo(() => unreadCount(notifications), [notifications]);

  const markRead = useCallback(
    async (id: string): Promise<Notification | null> => {
      const previous = notifications;
      const when = new Date().toISOString();
      setNotifications((current) =>
        current.map((item) =>
          item.id === id
            ? {
                ...item,
                is_read: true,
                is_unread: false,
                read_at: when,
              }
            : item,
        ),
      );
      setSaving(true);
      try {
        const updated = await api.markNotificationRead(id);
        if (mounted.current) {
          setNotifications((current) =>
            current.map((item) => (item.id === id ? updated : item)),
          );
        }
        return updated;
      } catch (cause) {
        if (mounted.current) {
          setNotifications(previous);
          setError(toApiError(cause).message);
        }
        return null;
      } finally {
        if (mounted.current) setSaving(false);
      }
    },
    [notifications],
  );

  const markAllRead = useCallback(async (): Promise<number> => {
    const previous = notifications;
    const when = new Date().toISOString();
    setNotifications((current) =>
      current.map((item) => ({
        ...item,
        is_read: true,
        is_unread: false,
        read_at: item.read_at ?? when,
      })),
    );
    setSaving(true);
    try {
      const result = await api.markAllRead(recipientId);
      return result.modified;
    } catch (cause) {
      if (mounted.current) {
        setNotifications(previous);
        setError(toApiError(cause).message);
      }
      return 0;
    } finally {
      if (mounted.current) setSaving(false);
    }
  }, [notifications, recipientId]);

  const savePreference = useCallback(
    async (input: PreferenceInput): Promise<Preference | null> => {
      setSaving(true);
      setError(null);
      try {
        const updated = await api.upsertPreference(input);
        if (mounted.current) {
          setPreferences((current: Preference[]) => {
            const matches = (item: Preference) =>
              item.channel === updated.channel && item.kind === updated.kind;
            return current.some(matches)
              ? current.map((item) => (matches(item) ? updated : item))
              : [...current, updated];
          });
        }
        return updated;
      } catch (cause) {
        if (mounted.current) setError(toApiError(cause).message);
        return null;
      } finally {
        if (mounted.current) setSaving(false);
      }
    },
    [],
  );

  return {
    notifications,
    filters,
    visible,
    unread,
    preferences,
    stats,
    period,
    loading,
    saving,
    error,
    setFilter,
    setPeriod,
    reload,
    markRead,
    markAllRead,
    savePreference,
  };
}

/** State returned by {@link useToastQueue}. */
export interface ToastQueueState {
  /** The visible toasts. */
  toasts: ToastItem[];
  /** Push a notification into the queue. */
  push: (notification: Notification) => void;
  /** Dismiss one toast. */
  dismiss: (id: string) => void;
  /** Dismiss every toast. */
  clear: () => void;
}

/**
 * Maintain a bounded toast queue with automatic dismissal.
 *
 * @param max - Maximum number of simultaneous toasts.
 * @returns The queue and its controls.
 */
export function useToastQueue(max = 4): ToastQueueState {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    if (toasts.length === 0) return undefined;
    const timer = window.setInterval(() => {
      const now = Date.now();
      setToasts((current) =>
        current.filter((toast) => !shouldAutoDismiss(toast, now)),
      );
    }, 500);
    return () => window.clearInterval(timer);
  }, [toasts.length]);

  const push = useCallback(
    (notification: Notification) => {
      setToasts((current) =>
        trimToasts([...current, makeToast(notification)], max),
      );
    },
    [max],
  );
  const dismiss = useCallback((id: string) => {
    setToasts((current) => dismissToast(current, id));
  }, []);
  const clear = useCallback(() => setToasts([]), []);

  return { toasts, push, dismiss, clear };
}

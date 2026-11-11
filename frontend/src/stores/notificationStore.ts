/**
 * Notification store: the transient messages surfaced by the dashboard.
 */

import { useMemo } from "react";
import { create } from "zustand";

/** The severity of a dashboard notification. */
export type NotificationTone = "info" | "success" | "warning" | "error";

/** A dashboard notification. */
export interface Notification {
  /** Unique identifier of the notification. */
  id: string;
  /** The severity of the notification. */
  tone: NotificationTone;
  /** The headline of the notification. */
  title: string;
  /** Optional supporting copy. */
  description?: string;
  /** The timestamp the notification was created at. */
  createdAt: number;
}

/** The maximum number of notifications kept in the store. */
export const MAX_NOTIFICATIONS = 50;

/** The state managed by the notification store. */
export interface NotificationState {
  /** The active notifications, newest first. */
  notifications: Notification[];
  /** Prepend a notification. */
  push: (notification: Omit<Notification, "id" | "createdAt">) => string;
  /** Remove a notification. */
  dismiss: (id: string) => void;
  /** Remove every notification. */
  clear: () => void;
}

let counter = 0;

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],

  push: (notification) => {
    counter += 1;
    const id = `notification-${counter}-${Date.now()}`;
    set((state) => ({
      notifications: [
        { ...notification, id, createdAt: Date.now() },
        ...state.notifications,
      ].slice(0, MAX_NOTIFICATIONS),
    }));
    return id;
  },

  dismiss: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((notification) => notification.id !== id),
    })),

  clear: () => set({ notifications: [] }),
}));

/**
 * Return the active notifications and the actions used to manage them.
 *
 * @returns The notifications and the actions.
 */
export function useNotifications(): {
  notifications: Notification[];
  notify: (notification: Omit<Notification, "id" | "createdAt">) => string;
  dismiss: (id: string) => void;
  clear: () => void;
} {
  const notifications = useNotificationStore((state) => state.notifications);
  const push = useNotificationStore((state) => state.push);
  const dismiss = useNotificationStore((state) => state.dismiss);
  const clear = useNotificationStore((state) => state.clear);

  return useMemo(
    () => ({ notifications, notify: push, dismiss, clear }),
    [notifications, push, dismiss, clear],
  );
}

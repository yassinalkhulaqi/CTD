/** Accessible toast queue with manual and automatic dismissal. */

import { AlertTriangle, Info, X } from "lucide-react";
import { Button } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { severityClass } from "../logic";
import type { ToastItem } from "../types";
import styles from "./ToastQueue.module.css";

/** Props accepted by {@link ToastQueue}. */
export interface ToastQueueProps {
  /** The active toasts. */
  toasts: ToastItem[];
  /** Called when a toast is dismissed. */
  onDismiss: (id: string) => void;
  /** Called to clear the whole queue. */
  onClear: () => void;
  /** Additional class name. */
  className?: string;
}

const ICONS = {
  info: <Info size={16} aria-hidden="true" />,
  warning: <AlertTriangle size={16} aria-hidden="true" />,
  critical: <AlertTriangle size={16} aria-hidden="true" />,
};

/**
 * Render the toast queue.
 *
 * @param props - The component props.
 * @returns The toast viewport.
 */
export function ToastQueue({
  toasts,
  onDismiss,
  onClear,
  className,
}: ToastQueueProps) {
  return (
    <section
      className={cn(styles.viewport, className)}
      aria-label="Notification toasts"
      data-testid="toast-queue"
    >
      {toasts.length > 0 ? (
        <Button
          size="sm"
          variant="ghost"
          className={styles.clear}
          onClick={onClear}
          aria-label="Dismiss all toasts"
        >
          Clear all
        </Button>
      ) : null}
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(styles.toast, styles[severityClass(toast.tone)])}
          role={toast.tone === "critical" ? "alert" : "status"}
          aria-live={toast.tone === "critical" ? "assertive" : "polite"}
          data-testid={`toast-${toast.id}`}
        >
          <span className={styles.icon} aria-hidden="true">
            {ICONS[toast.tone]}
          </span>
          <div className={styles.body}>
            <p className={styles.title}>{toast.notification.title}</p>
            <p className={styles.description}>{toast.notification.body}</p>
          </div>
          <button
            type="button"
            className={styles.dismiss}
            onClick={() => onDismiss(toast.id)}
            aria-label={`Dismiss ${toast.notification.title}`}
          >
            <X size={14} aria-hidden="true" />
          </button>
          {toast.ttl > 0 ? (
            <span
              className={styles.progress}
              style={{ animationDuration: `${toast.ttl}ms` }}
              aria-hidden="true"
            />
          ) : null}
        </div>
      ))}
    </section>
  );
}

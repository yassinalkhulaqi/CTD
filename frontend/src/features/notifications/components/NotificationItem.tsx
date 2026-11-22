/** One notification row in the centre's list. */

import { ArrowUpRight, Check, CheckCheck } from "lucide-react";
import { Badge, Button } from "../../../components/ui";
import { cn, formatRelativeTime } from "../../../lib/utils";
import { CHANNEL_LABELS, KIND_LABELS, severityClass } from "../logic";
import type { Notification } from "../types";
import { SeverityBadge } from "./SeverityBadge";
import styles from "./NotificationItem.module.css";

/** Props accepted by {@link NotificationItem}. */
export interface NotificationItemProps {
  /** The notification to render. */
  notification: Notification;
  /** Called when the row is acknowledged. */
  onMarkRead: (id: string) => void;
  /** Disable the row controls while a mutation is in flight. */
  busy?: boolean;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a single notification with its controls.
 *
 * @param props - The component props.
 * @returns The list item element.
 */
export function NotificationItem({
  notification,
  onMarkRead,
  busy = false,
  className,
}: NotificationItemProps) {
  return (
    <li
      className={cn(
        styles.item,
        notification.is_unread && styles.unread,
        styles[severityClass(notification.severity)],
        className,
      )}
      data-severity={notification.severity}
      data-testid={`notification-${notification.id}`}
    >
      <span className={styles.rail} aria-hidden="true" />
      <div className={styles.content}>
        <div className={styles.heading}>
          <h3 className={styles.title}>{notification.title}</h3>
          <SeverityBadge severity={notification.severity} />
        </div>
        <p className={styles.body}>{notification.body}</p>
        <div className={styles.meta}>
          <Badge tone="neutral" outline>
            {KIND_LABELS[notification.kind]}
          </Badge>
          <span className={styles.channel}>
            {CHANNEL_LABELS[notification.channel]}
          </span>
          <span className={styles.dot} aria-hidden="true">
            ·
          </span>
          <time dateTime={notification.created_at}>
            {formatRelativeTime(notification.created_at)}
          </time>
        </div>
      </div>
      <div className={styles.actions}>
        {notification.is_unread ? (
          <Button
            size="sm"
            variant="secondary"
            icon={<Check size={14} aria-hidden="true" />}
            onClick={() => onMarkRead(notification.id)}
            disabled={busy}
            aria-label={`Mark ${notification.title} as read`}
          >
            Mark read
          </Button>
        ) : (
          <span className={styles.read} aria-label="Already read">
            <CheckCheck size={15} aria-hidden="true" />
            Read
          </span>
        )}
        {notification.action_url ? (
          <a
            className={styles.link}
            href={notification.action_url}
            aria-label={`Open ${notification.title}`}
          >
            Open
            <ArrowUpRight size={13} aria-hidden="true" />
          </a>
        ) : null}
      </div>
    </li>
  );
}

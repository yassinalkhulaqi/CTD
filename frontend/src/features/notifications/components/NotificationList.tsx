/** Filterable list of notifications with loading, empty and error states. */

import { BellOff, CheckCheck, Search } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Input,
  Select,
  Skeleton,
  Switch,
} from "../../../components/ui";
import type { SelectOption } from "../../../components/ui";
import { KIND_LABELS, countByKind } from "../logic";
import type { Notification, NotificationFilters } from "../types";
import { NotificationItem } from "./NotificationItem";
import styles from "./NotificationList.module.css";

/** Props accepted by {@link NotificationList}. */
export interface NotificationListProps {
  /** Notifications to display after filtering. */
  notifications: Notification[];
  /** Every notification, used to build the kind filter counts. */
  allNotifications: Notification[];
  /** Active filters. */
  filters: NotificationFilters;
  /** Called when a filter changes. */
  onFilterChange: <K extends keyof NotificationFilters>(
    key: K,
    value: NotificationFilters[K],
  ) => void;
  /** Called when one notification is acknowledged. */
  onMarkRead: (id: string) => void;
  /** Called when all notifications are acknowledged. */
  onMarkAllRead: () => void;
  /** Number of unread notifications. */
  unread: number;
  /** Whether data is loading. */
  loading: boolean;
  /** Whether a mutation is in flight. */
  busy: boolean;
  /** Last error message. */
  error: string | null;
  /** Called to retry a failed load. */
  onRetry: () => void;
}

/**
 * Render the notification list and its filter controls.
 *
 * @param props - The component props.
 * @returns The list panel.
 */
export function NotificationList({
  notifications,
  allNotifications,
  filters,
  onFilterChange,
  onMarkRead,
  onMarkAllRead,
  unread,
  loading,
  busy,
  error,
  onRetry,
}: NotificationListProps) {
  const kindOptions: SelectOption[] = [
    { value: "all", label: "All kinds" },
    ...countByKind(allNotifications).map((entry) => ({
      value: entry.kind,
      label: `${KIND_LABELS[entry.kind]} (${entry.count})`,
    })),
  ];
  const severityOptions: SelectOption[] = [
    { value: "all", label: "All severities" },
    { value: "critical", label: "Critical" },
    { value: "warning", label: "Warning" },
    { value: "info", label: "Info" },
  ];

  return (
    <Card
      className={styles.panel}
      as="section"
      aria-labelledby="notification-list-title"
    >
      <CardHeader
        actions={
          <Button
            size="sm"
            variant="secondary"
            icon={<CheckCheck size={14} aria-hidden="true" />}
            onClick={onMarkAllRead}
            disabled={busy || unread === 0}
          >
            Mark all read
          </Button>
        }
      >
        <CardTitle level={2} id="notification-list-title">
          Inbox
          {unread > 0 ? (
            <span className={styles.count} aria-label={`${unread} unread`}>
              {unread}
            </span>
          ) : null}
        </CardTitle>
        <p className={styles.hint}>Urgent messages are shown first.</p>
      </CardHeader>
      <CardContent>
        <div className={styles.filters}>
          <Input
            aria-label="Search notifications"
            placeholder="Search notifications…"
            icon={<Search size={14} aria-hidden="true" />}
            value={filters.search}
            onChange={(event) => onFilterChange("search", event.target.value)}
          />
          <Select
            aria-label="Filter by kind"
            value={filters.kind}
            options={kindOptions}
            onChange={(event) =>
              onFilterChange(
                "kind",
                event.target.value as NotificationFilters["kind"],
              )
            }
          />
          <Select
            aria-label="Filter by severity"
            value={filters.severity}
            options={severityOptions}
            onChange={(event) =>
              onFilterChange(
                "severity",
                event.target.value as NotificationFilters["severity"],
              )
            }
          />
          <Switch
            checked={filters.unreadOnly}
            onChange={(event) =>
              onFilterChange("unreadOnly", event.target.checked)
            }
          >
            Unread only
          </Switch>
        </div>

        {error ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : loading ? (
          <div className={styles.skeletons} aria-label="Loading notifications">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} height={84} />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={<BellOff size={20} aria-hidden="true" />}
            title="Nothing to show"
            description="Try a different filter, or wait for the next event."
          />
        ) : (
          <ul className={styles.list} aria-label="Notifications">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkRead={onMarkRead}
                busy={busy}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

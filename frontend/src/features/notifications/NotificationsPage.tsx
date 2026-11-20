/** The routed notification centre screen. */

import { useEffect, useMemo, useState } from "react";
import { Bell, Plus, RefreshCw } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  ErrorState,
  Input,
  StatCard,
} from "../../components/ui";
import { toApiError } from "../../api/client";
import { formatPercent } from "../../lib/utils";
import * as api from "./api";
import {
  DigestPreview,
  NotificationList,
  PreferencePanel,
  ToastQueue,
} from "./components";
import { useNotificationCentre, useToastQueue } from "./hooks";
import { setQuietHours, togglePreference } from "./logic";
import type { Channel, DigestPreviewPayload, NotificationKind } from "./types";
import styles from "./NotificationsPage.module.css";

/** Default recipient used by the centre. */
const DEFAULT_RECIPIENT = "member-1";

/**
 * Render the notification centre route.
 *
 * @returns The page element.
 */
export function NotificationsPage() {
  const [recipientId, setRecipientId] = useState(DEFAULT_RECIPIENT);
  const centre = useNotificationCentre(recipientId);
  const toasts = useToastQueue();
  const [preview, setPreview] = useState<DigestPreviewPayload | null>(null);
  const [digestLoading, setDigestLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [sampleBusy, setSampleBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setDigestLoading(true);
    api
      .getDigestPreview(recipientId, centre.period)
      .then((result) => {
        if (active) setPreview(result);
      })
      .catch((cause: unknown) => {
        if (active) setActionError(toApiError(cause).message);
      })
      .finally(() => {
        if (active) setDigestLoading(false);
      });
    return () => {
      active = false;
    };
  }, [recipientId, centre.period]);

  const criticalCount = useMemo(
    () =>
      centre.notifications.filter(
        (item) => item.severity === "critical" && item.is_unread,
      ).length,
    [centre.notifications],
  );

  const changePreference = (
    channel: Channel,
    kind: NotificationKind,
    enabled: boolean,
  ): void => {
    const rows = togglePreference(centre.preferences, channel, kind, enabled);
    const target = rows.find(
      (row) => row.channel === channel && row.kind === kind,
    );
    if (target)
      void centre.savePreference({ ...target, recipient_id: recipientId });
  };

  const changeQuietHours = (
    channel: Channel,
    start: number,
    end: number,
  ): void => {
    const rows = setQuietHours(centre.preferences, channel, "*", start, end);
    const target = rows.find(
      (row) => row.channel === channel && row.kind === "*",
    );
    if (target)
      void centre.savePreference({ ...target, recipient_id: recipientId });
  };

  const saveAll = (): void => {
    void centre.reload();
  };

  const sendDigest = async (): Promise<void> => {
    setSending(true);
    setActionError(null);
    try {
      const digest = await api.buildDigest(recipientId, centre.period);
      await api.sendDigest(digest.id);
      setSent(true);
      setPreview(await api.getDigestPreview(recipientId, centre.period));
    } catch (cause) {
      setActionError(toApiError(cause).message);
    } finally {
      setSending(false);
    }
  };

  const emitSample = async (): Promise<void> => {
    setSampleBusy(true);
    setActionError(null);
    try {
      const result = await api.createNotification({
        recipient_id: recipientId,
        channel: "in_app",
        kind: "system",
        title: "Test notification",
        body: "The notification centre is connected.",
        severity: "warning",
      });
      if (result.delivered) toasts.push(result.notification);
      await centre.reload();
    } catch (cause) {
      setActionError(toApiError(cause).message);
    } finally {
      setSampleBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            <Bell size={22} aria-hidden="true" /> Notification centre
          </h1>
          <p className={styles.subtitle}>
            Review alerts, tune delivery and prepare digests in one place.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Input
            label="Recipient"
            hideLabel
            value={recipientId}
            onChange={(event) => setRecipientId(event.target.value)}
            aria-label="Recipient identifier"
          />
          <Button
            variant="secondary"
            icon={<RefreshCw size={15} aria-hidden="true" />}
            onClick={() => void centre.reload()}
            disabled={centre.loading}
          >
            Refresh
          </Button>
          <Button
            icon={<Plus size={15} aria-hidden="true" />}
            onClick={() => void emitSample()}
            loading={sampleBusy}
          >
            Send test
          </Button>
        </div>
      </header>

      {actionError ? (
        <ErrorState
          message={actionError}
          onRetry={() => {
            setActionError(null);
            void centre.reload();
          }}
        />
      ) : null}

      <div className={styles.stats} aria-label="Notification statistics">
        <StatCard
          label="Total"
          value={centre.stats.total}
          meta="all messages"
          icon={<Bell size={16} aria-hidden="true" />}
        />
        <StatCard
          label="Unread"
          value={centre.unread}
          meta="awaiting review"
          accent="var(--accent-base)"
        />
        <StatCard
          label="Critical"
          value={criticalCount}
          meta="needs attention"
          accent="var(--danger-base)"
        />
        <StatCard
          label="Read rate"
          value={formatPercent(centre.stats.read_rate, 0)}
          meta="acknowledged"
          accent="var(--success-base)"
        />
      </div>

      <div className={styles.layout}>
        <NotificationList
          notifications={centre.visible}
          allNotifications={centre.notifications}
          filters={centre.filters}
          onFilterChange={centre.setFilter}
          onMarkRead={(id) => void centre.markRead(id)}
          onMarkAllRead={() => void centre.markAllRead()}
          unread={centre.unread}
          loading={centre.loading}
          busy={centre.saving}
          error={centre.error}
          onRetry={() => void centre.reload()}
        />
        <aside className={styles.side}>
          <PreferencePanel
            preferences={centre.preferences}
            onToggle={changePreference}
            onQuietChange={changeQuietHours}
            onSave={saveAll}
            saving={centre.saving}
          />
          {digestLoading ? (
            <Card>
              <CardContent>Loading digest…</CardContent>
            </Card>
          ) : (
            <DigestPreview
              preview={preview}
              period={centre.period}
              onPeriodChange={(period) => {
                centre.setPeriod(period);
                setSent(false);
              }}
              onSend={() => void sendDigest()}
              sending={sending}
              sent={sent}
            />
          )}
        </aside>
      </div>

      <ToastQueue
        toasts={toasts.toasts}
        onDismiss={toasts.dismiss}
        onClear={toasts.clear}
      />
    </div>
  );
}

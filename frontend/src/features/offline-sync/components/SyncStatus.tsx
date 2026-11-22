/**
 * Sync health card with counters, progress and a manual sync action.
 */

import { AlertOctagon, CheckCircle2, Clock3, CloudUpload, Layers3 } from "lucide-react";
import { Badge, Button, Progress, StatCard } from "../../components/ui";
import { cn } from "../../lib/utils";
import { completionText, healthLabel, healthTone, syncButtonLabel } from "../sync";
import type { SyncStatus as SyncStatusModel } from "../types";
import styles from "./SyncStatus.module.css";

/** Props accepted by {@link SyncStatus}. */
export interface SyncStatusProps {
  /** Status summary returned by the API. */
  status: SyncStatusModel | null;
  /** Browser connectivity state. */
  online: boolean;
  /** Whether a sync action is in flight. */
  busy: boolean;
  /** Called when the manual sync button is pressed. */
  onSync: () => void;
  /** Additional class applied to the card. */
  className?: string;
}

/**
 * Render the status card including an explicit manual sync affordance.
 *
 * @param props - The component props.
 * @returns The status card element.
 */
export function SyncStatus({
  status,
  online,
  busy,
  onSync,
  className,
}: SyncStatusProps) {
  const pending = status?.pending ?? 0;
  const conflicts = status?.conflict ?? 0;
  const synced = status?.synced ?? 0;
  const health = status?.health_label ?? "idle";
  const tone = healthTone(health);

  return (
    <section
      className={cn(styles.card, className)}
      aria-labelledby="sync-status-heading"
    >
      <header className={styles.header}>
        <div>
          <h2 className={styles.heading} id="sync-status-heading">
            Sync status
          </h2>
          <p className={styles.subheading}>{healthLabel(health)}</p>
        </div>
        <Badge tone={tone} dot>
          {health}
        </Badge>
      </header>

      <div className={styles.stats}>
        <StatCard
          label="Pending"
          value={pending}
          meta="waiting to push"
          icon={<Clock3 size={16} />}
          accent="var(--warning-base)"
          loading={status === null}
        />
        <StatCard
          label="Conflicts"
          value={conflicts}
          meta="need a decision"
          icon={<AlertOctagon size={16} />}
          accent="var(--danger-base)"
          loading={status === null}
        />
        <StatCard
          label="Synced"
          value={synced}
          meta="applied to server"
          icon={<CheckCircle2 size={16} />}
          accent="var(--success-base)"
          loading={status === null}
        />
        <StatCard
          label="Attempts"
          value={status?.average_attempts ?? 0}
          meta="per mutation"
          icon={<Layers3 size={16} />}
          accent="var(--info-base)"
          loading={status === null}
        />
      </div>

      <div className={styles.progressArea}>
        <div className={styles.progressHeader}>
          <span>Completion</span>
          <span className={styles.progressValue}>{completionText(status)}</span>
        </div>
        <Progress
          value={status?.completion_rate ?? 0}
          tone={conflicts > 0 ? "danger" : pending > 0 ? "warning" : "success"}
          label="Synchronisation completion"
        />
      </div>

      <footer className={styles.footer}>
        <div className={styles.snapshot}>
          <CloudUpload size={16} aria-hidden="true" />
          <div>
            <p className={styles.snapshotTitle}>
              {status?.latest_snapshot
                ? `Snapshot v${status.latest_snapshot.version}`
                : "No snapshot yet"}
            </p>
            <p className={styles.snapshotMeta}>
              {status?.stale
                ? "Last sync may be out of date"
                : `${status?.resolution_count ?? 0} conflicts resolved`}
            </p>
          </div>
        </div>
        <Button
          icon={<CloudUpload size={15} />}
          onClick={onSync}
          disabled={!online}
          loading={busy}
          loadingLabel="Syncing"
          aria-describedby={!online ? "sync-offline-hint" : undefined}
        >
          {syncButtonLabel(online, busy, pending)}
        </Button>
        {!online ? (
          <p className={styles.offlineHint} id="sync-offline-hint">
            Reconnect to push queued changes.
          </p>
        ) : null}
      </footer>
    </section>
  );
}

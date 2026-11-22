/**
 * The routed Offline & Sync screen.
 */

import { useState } from "react";
import { AlertTriangle, ArrowRight, Cloud, ListChecks, WifiOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, ErrorState } from "../../components/ui";
import { ConflictDialog } from "./components/ConflictDialog";
import { ConnectivityBanner } from "./components/ConnectivityBanner";
import { OfflineBadge } from "./components/OfflineBadge";
import { QueueInspector } from "./components/QueueInspector";
import { SyncStatus } from "./components/SyncStatus";
import { useOfflineSync } from "./hooks";
import { conflictedMutations } from "./sync";
import type {
  ConflictStrategy,
  Payload,
  PendingMutation,
} from "./types";
import styles from "./OfflinePage.module.css";

/** Props accepted by {@link OfflinePage}. */
export interface OfflinePageProps {
  /** Optional client identifier used to scope the displayed queue. */
  clientId?: string;
}

/**
 * Render the complete offline queue and reconciliation workspace.
 *
 * @param props - The component props.
 * @returns The page element.
 */
export function OfflinePage({ clientId }: OfflinePageProps) {
  const controller = useOfflineSync(clientId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = controller.queue.find((item) => item.id === selectedId) ?? null;
  const conflicts = conflictedMutations(controller.queue);
  const pending = controller.status?.pending ?? 0;
  const connectivity = controller.online ? "online" : "offline";

  const handleSelect = (mutation: PendingMutation) => {
    setSelectedId((current) => (current === mutation.id ? null : mutation.id));
  };

  const handleResolve = async (
    mutationId: string,
    strategy: ConflictStrategy,
    note: string,
    remotePayload: Payload,
    basePayload: Payload,
  ): Promise<boolean> => {
    const resolved = await controller.resolve(mutationId, {
      strategy,
      note,
      remote_payload: remotePayload,
      base_payload: basePayload,
    });
    if (resolved) setSelectedId(null);
    return resolved;
  };

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Operations</p>
          <h1 className={styles.title}>Offline &amp; Sync</h1>
          <p className={styles.intro}>
            Keep working without a connection. Edits are queued in order and
            reconciled against the server when you are back online.
          </p>
        </div>
        <OfflineBadge
          online={controller.online}
          pending={pending}
          conflicts={conflicts.length}
        />
      </header>

      <ConnectivityBanner
        connectivity={connectivity}
        pending={pending}
        onRetry={() => void controller.refresh()}
      />

      {controller.error ? (
        <ErrorState
          title="Sync needs attention"
          message={controller.error}
          onRetry={() => void controller.refresh()}
          retryLabel="Reload"
        />
      ) : null}

      <SyncStatus
        status={controller.status}
        online={controller.online}
        busy={controller.busy}
        onSync={() => void controller.syncNow()}
      />

      <div className={styles.layout}>
        <QueueInspector
          mutations={controller.queue}
          loading={controller.loading}
          error={null}
          online={controller.online}
          selectedId={selectedId}
          busy={controller.busy}
          onSelect={handleSelect}
          onRefresh={() => void controller.refresh()}
          onClear={() => void controller.clear()}
        />

        <aside className={styles.aside} aria-label="Conflict and sync guidance">
          <Card as="section" className={styles.asideCard}>
            <CardHeader actions={<span className={styles.conflictCount}>{conflicts.length}</span>}>
              <CardTitle level={3}>Needs review</CardTitle>
            </CardHeader>
            <CardContent>
              {conflicts.length === 0 ? (
                <p className={styles.emptyCopy}>
                  No conflicts right now. Version changes will be listed here.
                </p>
              ) : (
                <ul className={styles.conflictList}>
                  {conflicts.map((mutation) => (
                    <li key={mutation.id}>
                      <button
                        type="button"
                        className={styles.conflictButton}
                        onClick={() => handleSelect(mutation)}
                      >
                        <AlertTriangle size={14} aria-hidden="true" />
                        <span>
                          <strong>{mutation.entity_label}</strong>
                          <small>
                            v{mutation.base_version} · {mutation.id.slice(-6)}
                          </small>
                        </span>
                        <ArrowRight size={14} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card as="section" className={styles.asideCard}>
            <CardHeader>
              <CardTitle level={3}>How sync works</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className={styles.steps}>
                <li>
                  <WifiOff size={14} aria-hidden="true" />
                  <span>Edits are captured locally with the server version they saw.</span>
                </li>
                <li>
                  <ListChecks size={14} aria-hidden="true" />
                  <span>The oldest pending mutation is replayed first.</span>
                </li>
                <li>
                  <Cloud size={14} aria-hidden="true" />
                  <span>Version mismatches pause for a field-level decision.</span>
                </li>
              </ol>
            </CardContent>
          </Card>
        </aside>
      </div>

      <ConflictDialog
        mutation={selected}
        open={selected !== null && selected.status === "conflict"}
        busy={controller.busy}
        error={controller.error}
        onClose={() => setSelectedId(null)}
        onResolve={handleResolve}
      />
    </div>
  );
}

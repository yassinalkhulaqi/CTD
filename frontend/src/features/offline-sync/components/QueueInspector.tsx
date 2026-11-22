/**
 * Filterable inspector for the offline mutation queue.
 */

import { useState } from "react";
import { Inbox, RefreshCw, Trash2 } from "lucide-react";
import { cn } from "../../../lib/utils";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  IconButton,
  Skeleton,
} from "../../../components/ui";
import { STATUS_FILTERS, summariseQueue } from "../sync";
import type { MutationStatus, PendingMutation } from "../types";
import { MutationRow } from "./MutationRow";
import styles from "./QueueInspector.module.css";

/** Props accepted by {@link QueueInspector}. */
export interface QueueInspectorProps {
  /** Mutations returned by the queue endpoint. */
  mutations: PendingMutation[];
  /** Whether the queue is still loading. */
  loading: boolean;
  /** Last load or action error. */
  error: string | null;
  /** Whether the browser is online. */
  online: boolean;
  /** Identifier of the selected mutation. */
  selectedId?: string | null;
  /** Whether a mutating action is in flight. */
  busy?: boolean;
  /** Called when a row is activated. */
  onSelect: (mutation: PendingMutation) => void;
  /** Called when the refresh button is pressed. */
  onRefresh: () => void;
  /** Called when synchronised entries should be cleared. */
  onClear: () => void;
}

/**
 * Render the queue with status filters and empty, loading and error states.
 *
 * @param props - The component props.
 * @returns The inspector card.
 */
export function QueueInspector({
  mutations,
  loading,
  error,
  online,
  selectedId,
  busy = false,
  onSelect,
  onRefresh,
  onClear,
}: QueueInspectorProps) {
  const [filter, setFilter] = useState<MutationStatus | "all">("all");
  const counts = summariseQueue(mutations);
  const visible =
    filter === "all"
      ? mutations
      : mutations.filter((mutation) => mutation.status === filter);

  return (
    <section className={styles.panel} aria-labelledby="queue-heading">
      <header className={styles.header}>
        <div>
          <h2 className={styles.heading} id="queue-heading">
            Mutation queue
          </h2>
          <p className={styles.description}>
            Oldest edits are replayed first when the connection returns.
          </p>
        </div>
        <IconButton
          icon={<RefreshCw size={15} />}
          label="Refresh queue"
          onClick={onRefresh}
          disabled={loading || busy}
        />
      </header>

      <div className={styles.filters} role="group" aria-label="Filter mutations by status">
        {STATUS_FILTERS.map((option) => {
          const count =
            option.value === "all"
              ? counts.total
              : counts[option.value as MutationStatus];
          return (
            <button
              key={option.value}
              type="button"
              className={cn(
                styles.filter,
                filter === option.value && styles.filterActive,
              )}
              aria-pressed={filter === option.value}
              onClick={() => setFilter(option.value)}
            >
              {option.label}
              <span className={styles.filterCount}>{count}</span>
            </button>
          );
        })}
      </div>

      <div className={styles.body}>
        {error ? (
          <ErrorState
            title="The queue could not be loaded"
            message={error}
            onRetry={onRefresh}
          />
        ) : loading ? (
          <div className={styles.skeletons} aria-label="Loading mutation queue">
            <Skeleton lines={4} />
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon={<Inbox size={20} />}
            title={filter === "all" ? "The queue is empty" : `No ${filter} mutations`}
            description={
              online
                ? "Edits captured while offline will appear here."
                : "Your edits are safe. They will appear here once they are recorded."
            }
          />
        ) : (
          <ul className={styles.list}>
            {visible.map((mutation) => (
              <MutationRow
                key={mutation.id}
                mutation={mutation}
                selected={mutation.id === selectedId}
                onSelect={onSelect}
              />
            ))}
          </ul>
        )}
      </div>

      <footer className={styles.footer}>
        <div className={styles.summary}>
          <Badge tone="warning">{counts.pending} pending</Badge>
          <Badge tone="danger">{counts.conflict} conflicts</Badge>
          <Badge tone="success">{counts.synced} synced</Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon={<Trash2 size={13} />}
          onClick={onClear}
          disabled={busy || counts.synced === 0}
        >
          Clear synced
        </Button>
      </footer>
    </section>
  );
}

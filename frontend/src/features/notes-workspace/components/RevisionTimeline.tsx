/**
 * Sidebar timeline showing the version history of a note.
 */

import { History } from "lucide-react";
import { cn } from "../../../lib/utils";
import { formatRelativeTime } from "../../../lib/utils";
import { Badge, EmptyState } from "../../../components/ui";
import type { NoteRevision } from "../types";
import styles from "./RevisionTimeline.module.css";

/** Props accepted by {@link RevisionTimeline}. */
export interface RevisionTimelineProps {
  /** The revisions to display. */
  revisions: NoteRevision[];
  /** The identifier of the revision currently previewed. */
  selectedId?: string | null;
  /** Called when a revision is activated. */
  onSelect: (revision: NoteRevision) => void;
}

/**
 * Render the revision timeline.
 *
 * @param props - The component props.
 * @returns The timeline element.
 */
export function RevisionTimeline({
  revisions,
  selectedId,
  onSelect,
}: RevisionTimelineProps) {
  return (
    <section className={styles.timeline} aria-label="Revision history">
      <div className={styles.heading}>
        <History size={14} aria-hidden="true" />
        <span>History</span>
        <Badge tone="neutral">{revisions.length}</Badge>
      </div>
      {revisions.length === 0 ? (
        <EmptyState
          title="No revisions"
          description="Saving a note creates a version snapshot."
        />
      ) : (
        <ol className={styles.list}>
          {revisions.map((revision) => (
            <li key={revision.id} className={styles.item}>
              <button
                type="button"
                className={cn(
                  styles.entry,
                  selectedId === revision.id && styles.entryActive,
                )}
                aria-pressed={selectedId === revision.id}
                onClick={() => onSelect(revision)}
              >
                <span className={styles.dot} aria-hidden="true" />
                <span className={styles.body}>
                  <span className={styles.top}>
                    <strong>Version {revision.version}</strong>
                    {revision.is_latest ? (
                      <Badge tone="accent" outline>
                        latest
                      </Badge>
                    ) : null}
                  </span>
                  <span className={styles.change}>
                    {revision.change_summary}
                  </span>
                  <span className={styles.detail}>
                    {revision.author_id} ·{" "}
                    {formatRelativeTime(revision.created_at)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

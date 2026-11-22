/**
 * Compact status strip rendered above the note editor.
 */

import { Clock3, FileText, History, Pin } from "lucide-react";
import { Badge } from "../../../components/ui";
import { formatRelativeTime } from "../../../lib/utils";
import { saveStateLabel } from "../logic";
import type { SaveState } from "../types";
import styles from "./NoteMetaBar.module.css";

/** Props accepted by {@link NoteMetaBar}. */
export interface NoteMetaBarProps {
  /** The number of words in the draft. */
  wordCount: number;
  /** Estimated reading time in minutes. */
  readingTime: number;
  /** The current note version. */
  version: number;
  /** The current save state. */
  saveState: SaveState;
  /** ISO timestamp of the last update. */
  updatedAt?: string;
  /** Whether the note is pinned. */
  pinned?: boolean;
}

/**
 * Render note statistics and the save-state indicator.
 *
 * @param props - The component props.
 * @returns The meta bar element.
 */
export function NoteMetaBar({
  wordCount,
  readingTime,
  version,
  saveState,
  updatedAt,
  pinned = false,
}: NoteMetaBarProps) {
  const tone =
    saveState === "saved"
      ? "success"
      : saveState === "error"
        ? "danger"
        : saveState === "saving"
          ? "info"
          : "warning";
  return (
    <div className={styles.metaBar} role="group" aria-label="Note details">
      <span className={styles.stat}>
        <FileText size={13} aria-hidden="true" />
        {wordCount} words
      </span>
      <span className={styles.stat}>
        <Clock3 size={13} aria-hidden="true" />
        {readingTime} min read
      </span>
      <span className={styles.stat}>
        <History size={13} aria-hidden="true" />v{version}
      </span>
      {updatedAt ? (
        <span className={styles.stat}>
          Updated {formatRelativeTime(updatedAt)}
        </span>
      ) : null}
      {pinned ? (
        <Badge tone="accent" dot>
          <Pin size={11} aria-hidden="true" /> Pinned
        </Badge>
      ) : null}
      <Badge tone={tone} pulse={saveState === "saving"}>
        <span className={styles.statusDot} aria-hidden="true" />
        <span aria-live="polite">{saveStateLabel(saveState)}</span>
      </Badge>
    </div>
  );
}

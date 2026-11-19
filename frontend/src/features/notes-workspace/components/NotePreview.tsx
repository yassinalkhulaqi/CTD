/**
 * Live, HTML-safe preview of the note body.
 */

import { Eye, RotateCcw } from "lucide-react";
import { Badge, Button } from "../../../components/ui";
import { renderMarkdownish } from "../logic";
import type { NoteEntry, NoteRevision } from "../types";
import styles from "./NotePreview.module.css";

/** Props accepted by {@link NotePreview}. */
export interface NotePreviewProps {
  /** The note currently being edited, when one exists. */
  note: NoteEntry | null;
  /** The draft body to preview. */
  body: string;
  /** The draft title to preview. */
  title: string;
  /** A historical revision shown instead of the draft. */
  revision?: NoteRevision | null;
  /** Called when the historical preview is dismissed. */
  onClearRevision?: () => void;
}

/**
 * Render the preview pane.
 *
 * @param props - The component props.
 * @returns The preview element.
 */
export function NotePreview({
  note,
  body,
  title,
  revision = null,
  onClearRevision,
}: NotePreviewProps) {
  const headingList = note?.headings ?? [];
  const html = renderMarkdownish(body);
  return (
    <div className={styles.preview}>
      <header className={styles.header}>
        <span className={styles.kicker}>
          <Eye size={13} aria-hidden="true" /> Live preview
        </span>
        {revision ? (
          <div className={styles.revisionBar}>
            <Badge tone="info">v{revision.version}</Badge>
            <Button
              size="sm"
              variant="ghost"
              icon={<RotateCcw size={12} />}
              onClick={onClearRevision}
            >
              Back to draft
            </Button>
          </div>
        ) : null}
      </header>
      <article className={styles.paper}>
        <h2 className={styles.title}>{title || "Untitled note"}</h2>
        {note ? (
          <p className={styles.meta}>
            {note.challenge_id} · {note.member_id}
          </p>
        ) : null}
        <div
          className={styles.content}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </article>
      {headingList.length > 0 && !revision ? (
        <nav className={styles.outline} aria-label="Note outline">
          <p className={styles.outlineTitle}>On this page</p>
          {headingList.map((heading) => (
            <a
              key={`${heading.line}-${heading.anchor}`}
              href={`#${heading.anchor}`}
              className={styles.outlineLink}
              style={{ paddingLeft: `${heading.indent * 12}px` }}
            >
              {heading.text}
            </a>
          ))}
        </nav>
      ) : null}
    </div>
  );
}

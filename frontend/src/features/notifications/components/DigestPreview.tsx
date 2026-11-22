/** Digest preview with period selection and dispatch controls. */

import { FileText, Send } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "../../../components/ui";
import { KIND_LABELS, digestGroupTotal, digestHeadline } from "../logic";
import type { DigestPeriod, DigestPreviewPayload } from "../types";
import { SeverityBadge } from "./SeverityBadge";
import styles from "./DigestPreview.module.css";

/** Periods selectable from the digest panel. */
const PERIODS: DigestPeriod[] = ["hourly", "daily", "weekly"];

/** Props accepted by {@link DigestPreview}. */
export interface DigestPreviewProps {
  /** The preview payload. */
  preview: DigestPreviewPayload | null;
  /** The currently selected period. */
  period: DigestPeriod;
  /** Called when the period changes. */
  onPeriodChange: (period: DigestPeriod) => void;
  /** Called to generate and dispatch a digest. */
  onSend: () => void;
  /** Whether a digest is being generated. */
  sending: boolean;
  /** Whether the most recent digest was sent. */
  sent: boolean;
}

/**
 * Render a grouped digest preview.
 *
 * @param props - The component props.
 * @returns The digest panel.
 */
export function DigestPreview({
  preview,
  period,
  onPeriodChange,
  onSend,
  sending,
  sent,
}: DigestPreviewProps) {
  return (
    <Card className={styles.panel} as="section" aria-labelledby="digest-title">
      <CardHeader
        actions={
          <Button
            size="sm"
            icon={<Send size={14} aria-hidden="true" />}
            onClick={onSend}
            disabled={sending || !preview || preview.total === 0}
          >
            {sent ? "Send again" : "Send digest"}
          </Button>
        }
      >
        <CardTitle level={2} id="digest-title">
          <FileText size={16} aria-hidden="true" /> Digest preview
        </CardTitle>
        <p className={styles.hint}>Grouped by kind and severity.</p>
      </CardHeader>
      <CardContent>
        <div className={styles.periods} role="group" aria-label="Digest period">
          {PERIODS.map((option) => (
            <button
              key={option}
              type="button"
              className={
                option === period ? styles.periodActive : styles.period
              }
              aria-pressed={option === period}
              onClick={() => onPeriodChange(option)}
            >
              {option}
            </button>
          ))}
        </div>

        <p className={styles.headline}>{digestHeadline(preview)}</p>

        {!preview || preview.total === 0 ? (
          <EmptyState
            title="No digest content"
            description="Events will appear here once they arrive in this period."
          />
        ) : (
          <>
            <div className={styles.summary}>
              <Badge tone="accent">{preview.total} total</Badge>
              <Badge tone="neutral">
                {digestGroupTotal(preview.groups)} grouped
              </Badge>
            </div>
            <ul className={styles.groups}>
              {preview.groups.map((group) => (
                <li
                  key={`${group.kind}-${group.severity}`}
                  className={styles.group}
                >
                  <div className={styles.groupHeader}>
                    <SeverityBadge severity={group.severity} />
                    <span className={styles.groupKind}>
                      {KIND_LABELS[group.kind]}
                    </span>
                    <Badge tone="neutral" outline>
                      {group.count}
                    </Badge>
                  </div>
                  <ul className={styles.entries}>
                    {group.entries.map((entry) => (
                      <li key={entry.notification_id} className={styles.entry}>
                        <span className={styles.entryTitle}>{entry.title}</span>
                        <span className={styles.entryBody}>{entry.body}</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
            <details className={styles.raw}>
              <summary>View markdown</summary>
              <pre>{preview.markdown}</pre>
            </details>
          </>
        )}
      </CardContent>
    </Card>
  );
}

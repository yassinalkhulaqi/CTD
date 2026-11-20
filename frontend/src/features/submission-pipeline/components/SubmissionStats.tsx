/**
 * Statistics cards summarising the submission queue.
 */

import {
  CheckCircle2,
  Clock3,
  Gauge,
  Inbox,
  Repeat2,
  Target,
  XCircle,
} from "lucide-react";
import { StatCard } from "../../../components/ui";
import { successPercent } from "../logic";
import type { QueueSummary, SubmissionStats } from "../types";
import styles from "./SubmissionStats.module.css";

/** Props accepted by {@link SubmissionStatsView}. */
export interface SubmissionStatsViewProps {
  /** Aggregated statistics, or `null` before the first load. */
  stats: SubmissionStats | null;
  /** Render skeleton values while data loads. */
  loading?: boolean;
  /** Summary of the most recent processing pass. */
  summary?: QueueSummary | null;
}

/**
 * Render the headline queue metrics.
 *
 * @param props - The component props.
 * @returns The statistics grid.
 */
export function SubmissionStatsView({
  stats,
  loading = false,
  summary = null,
}: SubmissionStatsViewProps) {
  const byStatus = stats?.by_status ?? {};
  const total = stats?.total ?? 0;
  const accepted = byStatus["accepted"] ?? 0;
  const rejected = byStatus["rejected"] ?? 0;
  const pending =
    stats?.pending ?? (byStatus["queued"] ?? 0) + (byStatus["retrying"] ?? 0);

  return (
    <section className={styles.section} aria-label="Submission statistics">
      <div className={styles.grid}>
        <StatCard
          label="Submissions"
          value={total}
          meta="All recorded flags"
          icon={<Inbox size={17} />}
          loading={loading}
          accent="#6366f1"
        />
        <StatCard
          label="Accepted"
          value={accepted}
          meta="Matched the challenge"
          icon={<CheckCircle2 size={17} />}
          loading={loading}
          accent="#10b981"
        />
        <StatCard
          label="Rejected"
          value={rejected}
          meta="Need a corrected flag"
          icon={<XCircle size={17} />}
          loading={loading}
          accent="#f43f5e"
        />
        <StatCard
          label="Pending"
          value={pending}
          meta="Queued or retrying"
          icon={<Clock3 size={17} />}
          loading={loading}
          accent="#f59e0b"
        />
        <StatCard
          label="Acceptance"
          value={`${successPercent(accepted, total)}%`}
          meta={`${stats?.attempts ?? 0} validation attempts`}
          icon={<Target size={17} />}
          loading={loading}
          accent="#38bdf8"
        />
        <StatCard
          label="Avg attempts"
          value={(stats?.average_attempts ?? 0).toFixed(2)}
          meta={`${stats?.retries ?? 0} retried submissions`}
          icon={<Gauge size={17} />}
          loading={loading}
          accent="#a855f7"
        />
      </div>
      {summary ? (
        <p className={styles.summary} role="status">
          <Repeat2 size={14} aria-hidden="true" />
          Last pass processed {summary.processed} submission
          {summary.processed === 1 ? "" : "s"}: {summary.accepted} accepted,{" "}
          {summary.rejected} rejected, {summary.remaining} still pending.
        </p>
      ) : null}
    </section>
  );
}

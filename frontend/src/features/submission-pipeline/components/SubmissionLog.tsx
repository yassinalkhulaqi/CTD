/**
 * Filterable live log of flag submissions.
 */

import { RefreshCw } from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  Select,
  Spinner,
} from "../../../components/ui";
import {
  canRetry,
  challengeLabel,
  formatRelative,
  memberLabel,
} from "../logic";
import { STATUS_META, type Submission, type SubmissionFilters } from "../types";
import type { ChallengeOption, MemberOption } from "../types";
import { RetryButton } from "./RetryButton";
import { StatusPipeline } from "./StatusPipeline";
import styles from "./SubmissionLog.module.css";

/** Props accepted by {@link SubmissionLog}. */
export interface SubmissionLogProps {
  /** Submissions to display. */
  submissions: Submission[];
  /** Challenges used to resolve identifiers. */
  challenges: ChallengeOption[];
  /** Members used to resolve identifiers. */
  members: MemberOption[];
  /** Current filters. */
  filters: SubmissionFilters;
  /** Called when a filter changes. */
  onFiltersChange: (patch: Partial<SubmissionFilters>) => void;
  /** Called when a retry is requested. */
  onRetry: (id: string) => void;
  /** Called when the refresh button is pressed. */
  onRefresh: () => void;
  /** Identifier of a submission currently being retried. */
  retryingId?: string | null;
  /** Render the loading state. */
  loading?: boolean;
  /** Error returned by the API. */
  error?: string | null;
}

/**
 * Render the filters and submission table.
 *
 * @param props - The component props.
 * @returns The live log.
 */
export function SubmissionLog({
  submissions,
  challenges,
  members,
  filters,
  onFiltersChange,
  onRetry,
  onRefresh,
  retryingId = null,
  loading = false,
  error = null,
}: SubmissionLogProps) {
  const statusOptions = [
    { value: "all", label: "All statuses" },
    ...Object.entries(STATUS_META).map(([value, meta]) => ({
      value,
      label: meta.label,
    })),
  ];
  const challengeOptions = [
    { value: "", label: "All challenges" },
    ...challenges.map((challenge) => ({
      value: challenge.id,
      label: challenge.title,
    })),
  ];
  const memberOptions = [
    { value: "", label: "All members" },
    ...members.map((member) => ({
      value: member.id,
      label: member.display_name || member.handle,
    })),
  ];

  return (
    <section className={styles.section} aria-label="Submission log">
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Live submission log</h2>
          <p className={styles.subtitle}>
            {submissions.length} submissions in view
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon={<RefreshCw size={14} />}
          onClick={onRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </header>

      <div className={styles.filters}>
        <Select
          label="Status filter"
          hideLabel
          value={filters.status}
          options={statusOptions}
          onChange={(event) =>
            onFiltersChange({
              status: event.target.value as SubmissionFilters["status"],
            })
          }
        />
        <Select
          label="Challenge filter"
          hideLabel
          value={filters.challenge_id}
          options={challengeOptions}
          onChange={(event) =>
            onFiltersChange({ challenge_id: event.target.value })
          }
        />
        <Select
          label="Member filter"
          hideLabel
          value={filters.member_id}
          options={memberOptions}
          onChange={(event) =>
            onFiltersChange({ member_id: event.target.value })
          }
        />
      </div>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      {loading && submissions.length === 0 ? (
        <div className={styles.loading}>
          <Spinner label="Loading submissions" />
          <span>Loading submissions…</span>
        </div>
      ) : submissions.length === 0 ? (
        <EmptyState
          title="No submissions yet"
          description="Submit a flag above to see it move through the validation pipeline."
        />
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Flag</th>
                <th scope="col">Challenge</th>
                <th scope="col">Member</th>
                <th scope="col">Pipeline</th>
                <th scope="col">Attempts</th>
                <th scope="col">Submitted</th>
                <th scope="col">
                  <span className={styles.srOnly}>Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((submission) => (
                <tr key={submission.id}>
                  <td>
                    <code className={styles.flag}>
                      {submission.flag_cipher}
                    </code>
                  </td>
                  <td>{challengeLabel(submission.challenge_id, challenges)}</td>
                  <td>{memberLabel(submission.member_id, members)}</td>
                  <td>
                    <div className={styles.pipelineCell}>
                      <StatusPipeline status={submission.status} compact />
                      <Badge tone={STATUS_META[submission.status].tone} dot>
                        {STATUS_META[submission.status].label}
                      </Badge>
                    </div>
                  </td>
                  <td className={styles.numeric}>{submission.attempts}</td>
                  <td className={styles.muted}>
                    {formatRelative(submission.created_at)}
                  </td>
                  <td className={styles.actionCell}>
                    <RetryButton
                      canRetry={canRetry(
                        submission.status,
                        submission.attempts,
                      )}
                      loading={retryingId === submission.id}
                      onRetry={() => onRetry(submission.id)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/**
 * Routed submissions screen: submission console, stats and live log.
 */

import { useEffect, useState } from "react";
import { ListFilter } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui";
import { SubmissionForm } from "./components/SubmissionForm";
import { SubmissionLog } from "./components/SubmissionLog";
import { StatusPipeline } from "./components/StatusPipeline";
import { SubmissionStatsView } from "./components/SubmissionStats";
import { useSubmissions } from "./hooks";
import styles from "./SubmissionsPage.module.css";

/** Auto-refresh interval of the live log, in milliseconds. */
const REFRESH_INTERVAL = 10_000;

/**
 * Render the submission pipeline workspace.
 *
 * @returns The routed page.
 */
export function SubmissionsPage() {
  const controller = useSubmissions();
  const { refresh } = controller;
  const [notice, setNotice] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const latest = controller.submissions[0];

  useEffect(() => {
    const timer = window.setInterval(() => {
      void refresh();
    }, REFRESH_INTERVAL);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const handleSubmit = async (draft: {
    challenge_id: string;
    member_id: string;
    flag: string;
  }) => {
    try {
      await controller.submitFlag(draft);
      setNotice("Flag queued and validated by the pipeline.");
    } catch {
      setNotice(null);
    }
  };

  const handleRetry = async (id: string) => {
    setRetryingId(id);
    try {
      await controller.retry(id);
      setNotice(
        "Retry scheduled. The backoff window applies before validation.",
      );
    } catch {
      setNotice(null);
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <h1 className={styles.title}>Submissions</h1>
          <p className={styles.subtitle}>
            Submit flags, watch validation, deduplicate attempts and retry
            rejected submissions.
          </p>
        </div>
      </header>

      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}
      {controller.error ? (
        <p className={styles.error} role="alert">
          {controller.error}
        </p>
      ) : null}

      <SubmissionStatsView
        stats={controller.stats}
        loading={controller.loading}
        summary={controller.lastSummary}
      />

      <div className={styles.workspace}>
        <Card as="section" className={styles.console}>
          <CardHeader>
            <CardTitle level={3}>Submission console</CardTitle>
            <CardDescription>
              Normalise, validate and enqueue a flag.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SubmissionForm
              challenges={controller.challenges}
              members={controller.members}
              rules={controller.rules}
              loading={controller.loading}
              busy={controller.busy}
              error={null}
              onSubmit={handleSubmit}
            />
          </CardContent>
        </Card>

        <Card as="section" className={styles.pipelinePanel}>
          <CardHeader>
            <CardTitle level={3}>Pipeline state</CardTitle>
            <CardDescription>
              Progress of the most recent submission.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {latest ? (
              <div className={styles.latest}>
                <StatusPipeline
                  status={latest.status}
                  attempts={latest.attempts}
                />
                <dl className={styles.details}>
                  <dt>Flag</dt>
                  <dd>
                    <code>{latest.flag_cipher}</code>
                  </dd>
                  <dt>Attempts</dt>
                  <dd>{latest.attempts}</dd>
                  <dt>Outcome</dt>
                  <dd>{latest.error ?? "Awaiting decision"}</dd>
                </dl>
              </div>
            ) : (
              <div className={styles.placeholder}>
                <ListFilter size={22} aria-hidden="true" />
                <p>No flag has entered the pipeline yet.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card as="section" bare className={styles.logCard}>
        <CardContent>
          <SubmissionLog
            submissions={controller.submissions}
            challenges={controller.challenges}
            members={controller.members}
            filters={controller.filters}
            onFiltersChange={controller.setFilters}
            onRetry={(id) => void handleRetry(id)}
            onRefresh={() => void controller.refresh()}
            retryingId={retryingId}
            loading={controller.loading}
            error={null}
          />
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Visual representation of the queued -> validating -> decision pipeline.
 */

import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  LoaderCircle,
  RotateCw,
} from "lucide-react";
import { Badge } from "../../../components/ui";
import { PIPELINE_STAGES, STATUS_META, type SubmissionStatus } from "../types";
import { stageFor } from "../logic";
import styles from "./StatusPipeline.module.css";

/** Props accepted by {@link StatusPipeline}. */
export interface StatusPipelineProps {
  /** Current submission status. */
  status: SubmissionStatus;
  /** Number of attempts already consumed. */
  attempts?: number;
  /** Hide the descriptive footer. */
  compact?: boolean;
}

/**
 * Render the pipeline stages reached by a submission.
 *
 * @param props - The component props.
 * @returns The pipeline visualisation.
 */
export function StatusPipeline({
  status,
  attempts = 0,
  compact = false,
}: StatusPipelineProps) {
  const { index, failed } = stageFor(status);
  const meta = STATUS_META[status];
  const icons = [
    <Circle key="queued" size={14} aria-hidden="true" />,
    <LoaderCircle key="validating" size={14} aria-hidden="true" />,
    failed ? (
      <AlertTriangle key="rejected" size={14} aria-hidden="true" />
    ) : (
      <CheckCircle2 key="accepted" size={14} aria-hidden="true" />
    ),
  ];

  return (
    <div
      className={`${styles.pipeline} ${compact ? styles.compact : ""}`}
      role="group"
      aria-label={`Submission pipeline: ${meta.label}`}
    >
      <ol className={styles.stages}>
        {PIPELINE_STAGES.map((stage, position) => {
          const done =
            position < index || (position === index && status === "accepted");
          const current = position === index && status !== "accepted";
          const failedStage = position === 2 && failed;
          const state = failedStage
            ? "failed"
            : done
              ? "done"
              : current
                ? "current"
                : "todo";
          return (
            <li
              key={stage}
              className={`${styles.stage} ${styles[state]}`}
              aria-current={current ? "step" : undefined}
            >
              <span className={styles.marker} aria-hidden="true">
                {failedStage ? (
                  icons[2]
                ) : done ? (
                  <CheckCircle2 size={14} />
                ) : (
                  icons[position]
                )}
              </span>
              <span className={styles.label}>{STATUS_META[stage].label}</span>
              {position < PIPELINE_STAGES.length - 1 ? (
                <span
                  className={`${styles.connector} ${done ? styles.connectorDone : ""}`}
                  aria-hidden="true"
                />
              ) : null}
            </li>
          );
        })}
      </ol>
      {!compact ? (
        <div className={styles.footer}>
          <Badge
            tone={meta.tone}
            dot
            pulse={status === "validating" || status === "retrying"}
          >
            {meta.label}
          </Badge>
          <span className={styles.description}>{meta.description}</span>
          {attempts > 0 ? (
            <span className={styles.attempts}>
              <RotateCw size={12} aria-hidden="true" />
              {attempts} {attempts === 1 ? "attempt" : "attempts"}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

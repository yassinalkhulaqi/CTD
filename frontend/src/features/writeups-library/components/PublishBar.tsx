/** Publication workflow control shown alongside the reader. */

import type { ReactNode } from "react";
import { Check, Rocket, RotateCcw, Send } from "lucide-react";
import { Button } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import type { Writeup, WriteupStatus } from "../types";
import styles from "./PublishBar.module.css";

/** Workflow actions surfaced by the publish bar. */
export type WorkflowAction = "submit" | "publish" | "withdraw";

/** Props accepted by {@link PublishBar}. */
export interface PublishBarProps {
  /** The writeup whose workflow is displayed. */
  writeup: Writeup;
  /** Whether an approving review has been recorded. */
  canPublish?: boolean;
  /** Called with the selected workflow action. */
  onAction: (action: WorkflowAction) => void;
  /** Disable buttons while a mutation is pending. */
  busy?: boolean;
}

const STEPS: WriteupStatus[] = ["draft", "review", "published"];
const STEP_LABELS = ["Draft", "Review", "Published"];

/**
 * Render the three-stage publication workflow and its primary action.
 *
 * @param props - The component props.
 * @returns The workflow panel.
 */
export function PublishBar({
  writeup,
  canPublish = false,
  onAction,
  busy = false,
}: PublishBarProps) {
  const current = STEPS.indexOf(writeup.status);
  const ready = writeup.word_count >= 40 && writeup.summary.trim().length > 0;

  const action: { key: WorkflowAction; label: string; icon: ReactNode } | null =
    writeup.status === "draft"
      ? { key: "submit", label: "Submit for review", icon: <Send size={15} /> }
      : writeup.status === "review"
        ? {
            key: "publish",
            label: "Publish writeup",
            icon: <Rocket size={15} />,
          }
        : { key: "withdraw", label: "Withdraw", icon: <RotateCcw size={15} /> };

  const disabled =
    busy ||
    (action?.key === "submit" && !ready) ||
    (action?.key === "publish" && !canPublish);

  return (
    <section className={styles.panel} aria-label="Publication workflow">
      <div className={styles.header}>
        <h2 className={styles.title}>Publication</h2>
        <span className={styles.stage}>Stage {current + 1} of 3</span>
      </div>
      <ol className={styles.steps}>
        {STEPS.map((step, index) => (
          <li
            key={step}
            className={cn(
              styles.step,
              index < current && styles.done,
              index === current && styles.current,
            )}
            aria-current={index === current ? "step" : undefined}
          >
            <span className={styles.dot}>
              {index < current ? (
                <Check size={12} strokeWidth={3} />
              ) : (
                index + 1
              )}
            </span>
            <span className={styles.stepLabel}>{STEP_LABELS[index]}</span>
          </li>
        ))}
      </ol>
      {action ? (
        <Button
          icon={action.icon}
          variant={action.key === "withdraw" ? "secondary" : "primary"}
          block
          disabled={disabled}
          loading={busy}
          onClick={() => onAction(action.key)}
        >
          {action.label}
        </Button>
      ) : null}
      {action?.key === "submit" && !ready ? (
        <p className={styles.hint}>
          Add a summary and at least 40 words before submitting.
        </p>
      ) : null}
      {action?.key === "publish" && !canPublish ? (
        <p className={styles.hint}>
          An approving review is required before publishing.
        </p>
      ) : null}
    </section>
  );
}

/**
 * Progress header and resume banner of the wizard.
 */

import { Play, RotateCcw, Sparkles } from "lucide-react";
import { Badge, Button, Card, ScoreRing } from "../../../components/ui";
import { resumeMessage } from "../tour";
import type { Checklist, ResumeState } from "../types";
import styles from "./ProgressBanner.module.css";

/** Props accepted by {@link ProgressBanner}. */
export interface ProgressBannerProps {
  /** Overall completion percentage. */
  percent: number;
  /** Number of completed steps. */
  completed: number;
  /** Number of catalogue steps. */
  total: number;
  /** Status label returned by the API. */
  status: string;
  /** Resume state returned by the API. */
  resume: ResumeState | null;
  /** Checklist used for the supporting message. */
  checklist: Checklist | null;
  /** Start or reopen the tour. */
  onStart: () => void;
  /** Resume at the next unresolved step. */
  onResume: () => void;
  /** Clear progress and start over. */
  onRestart: () => void;
  /** Whether a reset mutation is in flight. */
  busy?: boolean;
}

/**
 * Render the progress summary and contextual resume call to action.
 *
 * @param props - The component props.
 * @returns The banner element.
 */
export function ProgressBanner({
  percent,
  completed,
  total,
  status,
  resume,
  checklist,
  onStart,
  onResume,
  onRestart,
  busy = false,
}: ProgressBannerProps) {
  const canResume = resume?.can_resume ?? false;
  const message = resumeMessage(checklist, percent);
  return (
    <Card
      className={styles.banner}
      as="section"
      aria-labelledby="onboarding-banner-title"
    >
      <div className={styles.lead}>
        <ScoreRing value={percent / 100} size={72} strokeWidth={6}>
          <span className={styles.ringValue}>{percent}%</span>
        </ScoreRing>
        <div className={styles.copy}>
          <div className={styles.eyebrow}>
            <Sparkles size={14} aria-hidden="true" />
            <span>Getting started</span>
            <Badge tone={status === "complete" ? "success" : "accent"} outline>
              {status}
            </Badge>
          </div>
          <h1 id="onboarding-banner-title" className={styles.title}>
            Set up your workspace
          </h1>
          <p className={styles.description}>
            {completed} of {total} tour steps finished. {message}
          </p>
        </div>
      </div>
      <div className={styles.actions}>
        {canResume ? (
          <Button icon={<Play size={14} />} onClick={onResume}>
            Resume tour
          </Button>
        ) : (
          <Button icon={<Play size={14} />} onClick={onStart}>
            {status === "complete" ? "Take the tour again" : "Start tour"}
          </Button>
        )}
        <Button
          variant="secondary"
          icon={<RotateCcw size={14} />}
          onClick={onRestart}
          disabled={busy || (completed === 0 && !canResume)}
        >
          Reset progress
        </Button>
      </div>
    </Card>
  );
}

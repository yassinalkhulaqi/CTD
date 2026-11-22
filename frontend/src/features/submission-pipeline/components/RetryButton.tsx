/**
 * Retry affordance for rejected submissions.
 */

import { RotateCcw } from "lucide-react";
import { Button } from "../../../components/ui";
import styles from "./RetryButton.module.css";

/** Props accepted by {@link RetryButton}. */
export interface RetryButtonProps {
  /** Whether the retry budget and status allow another attempt. */
  canRetry: boolean;
  /** Called when the user requests a retry. */
  onRetry: () => void;
  /** Disable interaction while the request is in flight. */
  loading?: boolean;
  /** Attempts already consumed, shown in the tooltip. */
  attempts?: number;
  /** Maximum attempts allowed by the policy. */
  maxAttempts?: number;
}

/**
 * Render a compact retry button with a helpful disabled explanation.
 *
 * @param props - The component props.
 * @returns The retry button.
 */
export function RetryButton({
  canRetry,
  onRetry,
  loading = false,
  attempts = 0,
  maxAttempts = 3,
}: RetryButtonProps) {
  const reason = !canRetry
    ? attempts >= maxAttempts
      ? "Retry budget exhausted"
      : "Only rejected submissions can be retried"
    : undefined;

  return (
    <Button
      className={styles.button}
      variant="secondary"
      size="sm"
      icon={<RotateCcw size={13} />}
      onClick={onRetry}
      disabled={!canRetry}
      loading={loading}
      loadingLabel="Scheduling retry"
      title={reason}
      aria-label="Retry submission"
    >
      Retry
    </Button>
  );
}

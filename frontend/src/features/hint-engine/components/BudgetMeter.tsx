/** Progress ring and reset control for a team's hint budget. */

import { RotateCcw } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../components/ui";
import {
  budgetUsage,
  formatCredits,
  formatTimestamp,
  ringGeometry,
} from "../hints";
import type { HintBudget } from "../types";
import styles from "./BudgetMeter.module.css";

/** Props accepted by {@link BudgetMeter}. */
export interface BudgetMeterProps {
  budget: HintBudget | null;
  onReset?: () => void;
  resetting?: boolean;
  teamLabel?: string;
}

const SIZE = 112;
const STROKE = 9;

/**
 * Render a circular budget meter with a reset affordance.
 *
 * @param props - The component props.
 * @returns The budget card.
 */
export function BudgetMeter({
  budget,
  onReset,
  resetting = false,
  teamLabel,
}: BudgetMeterProps) {
  const usage = budgetUsage(budget);
  const geometry = ringGeometry(usage.utilization, SIZE, STROKE);
  const color =
    usage.utilization >= 0.9 ? "var(--danger-base)" : "var(--accent-base)";

  return (
    <Card className={styles.card}>
      <CardHeader
        actions={
          onReset ? (
            <Button
              variant="ghost"
              size="sm"
              icon={<RotateCcw size={14} />}
              onClick={onReset}
              loading={resetting}
              loadingLabel="Resetting"
            >
              Reset
            </Button>
          ) : undefined
        }
      >
        <CardTitle level={3}>Team budget</CardTitle>
      </CardHeader>
      <CardContent className={styles.content}>
        <div
          className={styles.ring}
          role="img"
          aria-label={`${geometry.percent}% of the hint budget used, ${usage.remaining} credits left`}
        >
          <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            aria-hidden="true"
          >
            <circle
              className={styles.track}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={geometry.radius}
              strokeWidth={STROKE}
              fill="none"
            />
            <circle
              className={styles.progress}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={geometry.radius}
              strokeWidth={STROKE}
              stroke={color}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={geometry.circumference}
              strokeDashoffset={geometry.offset}
              transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
            />
          </svg>
          <div className={styles.center}>
            <span className={styles.value}>
              {formatCredits(usage.remaining)}
            </span>
            <span className={styles.unit}>credits left</span>
          </div>
        </div>
        <dl className={styles.details}>
          <div className={styles.detail}>
            <dt>Spent</dt>
            <dd>{formatCredits(usage.spent)}</dd>
          </div>
          <div className={styles.detail}>
            <dt>Allowance</dt>
            <dd>{formatCredits(usage.total)}</dd>
          </div>
          <div className={styles.detail}>
            <dt>Resets</dt>
            <dd>{formatTimestamp(budget?.reset_at ?? null)}</dd>
          </div>
          {teamLabel ? (
            <div className={styles.detail}>
              <dt>Team</dt>
              <dd>{teamLabel}</dd>
            </div>
          ) : null}
        </dl>
      </CardContent>
    </Card>
  );
}

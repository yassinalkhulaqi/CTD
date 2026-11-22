/** Countdown ring with a live, per-second progress arc. */

import { useId } from "react";
import { cn } from "../../../lib/utils";
import {
  countdownSeconds,
  deriveEventStatus,
  formatCountdown,
  ringProgress,
} from "../utils";
import type { CtfEvent } from "../types";
import styles from "./CountdownRing.module.css";

/** Props accepted by {@link CountdownRing}. */
export interface CountdownRingProps {
  event: CtfEvent;
  now: number;
  size?: number;
  label?: string;
  className?: string;
}

/**
 * Render a circular countdown for the current lifecycle phase.
 *
 * @param props - The component props.
 * @returns The countdown ring.
 */
export function CountdownRing({
  event,
  now,
  size = 84,
  label = "Time remaining",
  className,
}: CountdownRingProps) {
  const gradientId = useId();
  const seconds = countdownSeconds(event, now);
  const progress = ringProgress(event, now);
  const status = deriveEventStatus(event, now);
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - progress);
  const text = formatCountdown(seconds);

  return (
    <div
      className={cn(styles.ring, status === "live" && styles.live, className)}
      style={{ width: size, height: size }}
      role="timer"
      aria-label={`${label}: ${text}`}
    >
      <svg width={size} height={size} aria-hidden="true" className={styles.svg}>
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--accent-base)" />
            <stop offset="100%" stopColor="var(--info-base)" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-sunken)"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className={styles.progress}
        />
      </svg>
      <span className={styles.text}>{text}</span>
    </div>
  );
}

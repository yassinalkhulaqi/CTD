/**
 * A circular progress indicator used on badge cards and detail sheets.
 */

import type { ReactNode } from "react";
import { cn, clamp } from "../../../lib/utils";
import { progressRatio } from "../types";
import styles from "./ProgressRing.module.css";

/** Props accepted by {@link ProgressRing}. */
export interface ProgressRingProps {
  /** Completion percentage between 0 and 100. */
  value: number;
  /** Outer diameter in pixels. */
  size?: number;
  /** Stroke thickness in pixels. */
  strokeWidth?: number;
  /** Stroke colour, typically the tier accent. */
  color?: string;
  /** Accessible label for the indicator. */
  label: string;
  /** Play the unlock celebration animation. */
  celebrate?: boolean;
  /** Content rendered in the centre of the ring. */
  children?: ReactNode;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a determinate circular progress indicator.
 *
 * @param props - The component props.
 * @returns The ring element.
 */
export function ProgressRing({
  value,
  size = 72,
  strokeWidth = 6,
  color = "var(--accent-base)",
  label,
  celebrate = false,
  children,
  className,
}: ProgressRingProps) {
  const ratio = progressRatio(value);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamp(ratio, 0, 1));
  const rounded = Math.round(clamp(value, 0, 100));

  return (
    <div
      className={cn(styles.ring, celebrate && styles.celebrate, className)}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-label={label}
      aria-valuenow={rounded}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className={styles.svg}
        aria-hidden="true"
        focusable="false"
      >
        <circle
          className={styles.track}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
        />
        <circle
          className={styles.value}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className={styles.center}>{children ?? `${rounded}%`}</span>
    </div>
  );
}

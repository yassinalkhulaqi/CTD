/**
 * Feedback primitives: skeletons, spinners, empty and error states, progress.
 */

import type { HTMLAttributes, ReactNode } from "react";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";
import styles from "./Feedback.module.css";

/** Props accepted by {@link Skeleton}. */
export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** The width of the skeleton. */
  width?: number | string;
  /** The height of the skeleton. */
  height?: number | string;
  /** Render the skeleton as a circle. */
  circle?: boolean;
  /** Number of skeleton lines to render. */
  lines?: number;
}

/**
 * Render a shimmering placeholder block.
 *
 * @param props - The component props.
 * @returns The skeleton element.
 */
export function Skeleton({
  width,
  height,
  circle = false,
  lines,
  className,
  style,
  ...rest
}: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div
        className={cn(styles.skeletonGroup, className)}
        aria-hidden="true"
        {...rest}
      >
        {Array.from({ length: lines }, (_, index) => (
          <div
            key={index}
            className={styles.skeleton}
            style={{
              width: index === lines - 1 ? "65%" : "100%",
              height: height ?? 12,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        styles.skeleton,
        circle && styles.skeletonCircle,
        className,
      )}
      style={{
        width,
        height,
        borderRadius: circle ? "50%" : undefined,
        ...style,
      }}
      aria-hidden="true"
      {...rest}
    />
  );
}

/** Props accepted by {@link Spinner}. */
export interface SpinnerProps extends HTMLAttributes<HTMLSpanElement> {
  /** The size of the spinner in pixels. */
  size?: number;
  /** Accessible label announced while loading. */
  label?: string;
}

/**
 * Render an accessible loading indicator.
 *
 * @param props - The component props.
 * @returns The spinner element.
 */
export function Spinner({
  size = 18,
  label = "Loading",
  className,
  ...rest
}: SpinnerProps) {
  return (
    <span
      className={cn(styles.spinner, className)}
      style={{ width: size, height: size }}
      role="status"
      aria-label={label}
      {...rest}
    />
  );
}

/** Props accepted by {@link EmptyState}. */
export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  /** The headline of the empty state. */
  title: string;
  /** Supporting copy explaining the state. */
  description?: string;
  /** The icon rendered above the title. */
  icon?: ReactNode;
  /** The call to action. */
  action?: ReactNode;
}

/**
 * Render a friendly empty state.
 *
 * @param props - The component props.
 * @returns The empty state element.
 */
export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
  ...rest
}: EmptyStateProps) {
  return (
    <div className={cn(styles.empty, className)} role="status" {...rest}>
      <div className={styles.emptyIcon} aria-hidden="true">
        {icon ?? <Inbox size={22} />}
      </div>
      <p className={styles.emptyTitle}>{title}</p>
      {description ? (
        <p className={styles.emptyDescription}>{description}</p>
      ) : null}
      {action ? <div className={styles.emptyAction}>{action}</div> : null}
    </div>
  );
}

/** Props accepted by {@link ErrorState}. */
export interface ErrorStateProps extends HTMLAttributes<HTMLDivElement> {
  /** The headline of the error. */
  title?: string;
  /** The error message. */
  message?: string;
  /** Called when the retry button is pressed. */
  onRetry?: () => void;
  /** Label of the retry button. */
  retryLabel?: string;
}

/**
 * Render an error state with an optional retry action.
 *
 * @param props - The component props.
 * @returns The error state element.
 */
export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Try again",
  className,
  ...rest
}: ErrorStateProps) {
  return (
    <div className={cn(styles.errorState, className)} role="alert" {...rest}>
      <div className={styles.errorIcon} aria-hidden="true">
        <AlertTriangle size={20} />
      </div>
      <div className={styles.errorBody}>
        <p className={styles.errorTitle}>{title}</p>
        {message ? <p className={styles.errorMessage}>{message}</p> : null}
      </div>
      {onRetry ? (
        <Button
          variant="secondary"
          size="sm"
          icon={<RefreshCw size={14} />}
          onClick={onRetry}
          className={styles.errorAction}
        >
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}

/** Props accepted by {@link Progress}. */
export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  /** The completion ratio between 0 and 1. */
  value: number;
  /** The maximum value of the bar. */
  max?: number;
  /** The visual variant of the bar. */
  tone?: "accent" | "success" | "warning" | "danger";
  /** Render the bar as a thin strip. */
  thin?: boolean;
  /** Accessible label of the progress bar. */
  label?: string;
}

/**
 * Render a determinate progress bar.
 *
 * @param props - The component props.
 * @returns The progress element.
 */
export function Progress({
  value,
  max = 100,
  tone = "accent",
  thin = false,
  label,
  className,
  ...rest
}: ProgressProps) {
  const ratio = max === 0 ? 0 : Math.min(1, Math.max(0, value / max));
  return (
    <div
      className={cn(styles.progress, thin && styles.progressThin, className)}
      role="progressbar"
      aria-valuenow={Math.round(ratio * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      {...rest}
    >
      <div
        className={cn(styles.progressFill, styles[`progress-${tone}`])}
        style={{ width: `${ratio * 100}%` }}
      />
    </div>
  );
}

/** Props accepted by {@link ScoreRing}. */
export interface ScoreRingProps extends HTMLAttributes<HTMLDivElement> {
  /** The completion ratio between 0 and 1. */
  value: number;
  /** The size of the ring in pixels. */
  size?: number;
  /** The thickness of the ring stroke. */
  strokeWidth?: number;
  /** The accent colour of the ring. */
  color?: string;
  /** The content rendered inside the ring. */
  children?: ReactNode;
}

/**
 * Render a circular progress indicator.
 *
 * @param props - The component props.
 * @returns The ring element.
 */
export function ScoreRing({
  value,
  size = 56,
  strokeWidth = 5,
  color = "var(--accent-base)",
  children,
  className,
  ...rest
}: ScoreRingProps) {
  const ratio = Math.min(1, Math.max(0, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - ratio);

  return (
    <div
      className={cn(styles.ring, className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${Math.round(ratio * 100)}% complete`}
      {...rest}
    >
      <svg
        width={size}
        height={size}
        className={styles.ringSvg}
        aria-hidden="true"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-sunken)"
          strokeWidth={strokeWidth}
        />
        <circle
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
          className={styles.ringProgress}
        />
      </svg>
      <span className={styles.ringLabel}>
        {children ?? `${Math.round(ratio * 100)}%`}
      </span>
    </div>
  );
}

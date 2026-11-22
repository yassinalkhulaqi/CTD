/**
 * Illustrated empty states for the onboarding feature.
 *
 * The illustrations are inline SVG so they inherit theme colours and need no
 * image assets or network requests.
 */

import { ArrowRight } from "lucide-react";
import { cn } from "../../../lib/utils";
import { Button } from "../../../components/ui";
import styles from "./EmptyState.module.css";

/** The illustration shown above an empty state. */
export type EmptyStateVariant = "compass" | "checklist" | "sparkles";

/** Props accepted by {@link EmptyState}. */
export interface EmptyStateProps {
  /** Headline of the empty state. */
  title: string;
  /** Supporting copy. */
  description?: string;
  /** Label of the optional call to action. */
  actionLabel?: string;
  /** Called when the call to action is pressed. */
  onAction?: () => void;
  /** Illustration variant. */
  variant?: EmptyStateVariant;
  /** Optional extra class names. */
  className?: string;
}

/**
 * Render an SVG illustration matched to an empty state variant.
 *
 * @param variant - The illustration to draw.
 * @returns The illustration element.
 */
function Illustration({ variant }: { variant: EmptyStateVariant }) {
  if (variant === "checklist") {
    return (
      <svg viewBox="0 0 120 96" className={styles.svg} aria-hidden="true">
        <rect
          x="26"
          y="14"
          width="68"
          height="68"
          rx="10"
          className={styles.paper}
        />
        <rect
          x="38"
          y="28"
          width="10"
          height="10"
          rx="2"
          className={styles.box}
        />
        <rect
          x="56"
          y="31"
          width="30"
          height="4"
          rx="2"
          className={styles.line}
        />
        <rect
          x="38"
          y="46"
          width="10"
          height="10"
          rx="2"
          className={styles.box}
        />
        <rect
          x="56"
          y="49"
          width="24"
          height="4"
          rx="2"
          className={styles.line}
        />
        <rect
          x="38"
          y="64"
          width="10"
          height="10"
          rx="2"
          className={styles.box}
        />
        <rect
          x="56"
          y="67"
          width="18"
          height="4"
          rx="2"
          className={styles.line}
        />
        <path d="M39 69l3 3 6-7" className={styles.check} />
      </svg>
    );
  }
  if (variant === "sparkles") {
    return (
      <svg viewBox="0 0 120 96" className={styles.svg} aria-hidden="true">
        <circle cx="60" cy="48" r="26" className={styles.halo} />
        <path
          d="M60 24l5 17 17 5-17 5-5 17-5-17-17-5 17-5z"
          className={styles.spark}
        />
        <circle cx="92" cy="22" r="4" className={styles.dot} />
        <circle cx="26" cy="70" r="3" className={styles.dot} />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 120 96" className={styles.svg} aria-hidden="true">
      <circle cx="60" cy="48" r="30" className={styles.halo} />
      <circle cx="60" cy="48" r="23" className={styles.ring} />
      <path d="M60 34l7 14-7 14-7-14z" className={styles.needle} />
      <circle cx="60" cy="48" r="3" className={styles.dot} />
      <path d="M60 12v6M60 78v6M24 48h6M90 48h6" className={styles.ticks} />
    </svg>
  );
}

/**
 * Render a friendly empty state with an optional action.
 *
 * @param props - The component props.
 * @returns The empty state element.
 */
export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  variant = "compass",
  className,
}: EmptyStateProps) {
  return (
    <div className={cn(styles.empty, className)} role="status">
      <div className={styles.art}>
        <Illustration variant={variant} />
      </div>
      <p className={styles.title}>{title}</p>
      {description ? <p className={styles.description}>{description}</p> : null}
      {actionLabel && onAction ? (
        <Button
          size="sm"
          variant="secondary"
          onClick={onAction}
          trailingIcon={<ArrowRight size={14} />}
        >
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

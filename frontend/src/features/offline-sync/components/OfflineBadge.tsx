/**
 * Compact badge summarising connectivity and queue health at a glance.
 */

import type { ReactNode } from "react";
import { AlertTriangle, Check, CloudOff, RefreshCw } from "lucide-react";
import { Badge } from "../../components/ui";
import type { StatusTone } from "../types";
import styles from "./OfflineBadge.module.css";

/** Props accepted by {@link OfflineBadge}. */
export interface OfflineBadgeProps {
  /** Whether the browser currently has connectivity. */
  online: boolean;
  /** Number of pending mutations. */
  pending: number;
  /** Number of conflicted mutations. */
  conflicts: number;
  /** Hide the icon for dense layouts. */
  compact?: boolean;
  /** Additional class applied to the badge wrapper. */
  className?: string;
}

interface BadgeState {
  label: string;
  tone: StatusTone;
  icon: ReactNode;
}

/**
 * Render the most urgent connectivity or queue state.
 *
 * @param props - The component props.
 * @returns The badge element.
 */
export function OfflineBadge({
  online,
  pending,
  conflicts,
  compact = false,
  className,
}: OfflineBadgeProps) {
  let state: BadgeState;
  if (!online) {
    state = {
      label: "Offline",
      tone: "warning",
      icon: <CloudOff size={12} aria-hidden="true" />,
    };
  } else if (conflicts > 0) {
    state = {
      label: `${conflicts} conflict${conflicts === 1 ? "" : "s"}`,
      tone: "danger",
      icon: <AlertTriangle size={12} aria-hidden="true" />,
    };
  } else if (pending > 0) {
    state = {
      label: `${pending} queued`,
      tone: "info",
      icon: <RefreshCw size={12} aria-hidden="true" />,
    };
  } else {
    state = {
      label: "Up to date",
      tone: "success",
      icon: <Check size={12} aria-hidden="true" />,
    };
  }

  return (
    <span className={[styles.wrapper, className].filter(Boolean).join(" ")}>
      {compact ? null : state.icon}
      <Badge tone={state.tone} dot={compact} data-badge-state={state.label}>
        {state.label}
      </Badge>
    </span>
  );
}

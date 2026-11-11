/**
 * A live connection indicator for the dashboard header.
 */

import { Radio, WifiOff } from "lucide-react";
import { cn } from "../../lib/utils";
import { useRealtime } from "../../realtime/RealtimeProvider";
import { Tooltip } from "../ui";
import styles from "./ConnectionBadge.module.css";

const LABELS: Record<string, string> = {
  idle: "Realtime is idle",
  connecting: "Connecting to the realtime channel…",
  open: "Live — receiving events",
  reconnecting: "Reconnecting to the realtime channel…",
  closed: "The realtime channel is closed",
};

/** Props accepted by {@link ConnectionBadge}. */
export interface ConnectionBadgeProps {
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render the state of the realtime connection.
 *
 * @param props - The component props.
 * @returns The badge element.
 */
export function ConnectionBadge({ className }: ConnectionBadgeProps) {
  const { state, received } = useRealtime();
  const live = state === "open";

  return (
    <Tooltip content={LABELS[state] ?? state}>
      <span className={cn(styles.badge, styles[state], className)} data-state={state}>
        {live ? <Radio size={13} aria-hidden="true" /> : <WifiOff size={13} aria-hidden="true" />}
        <span className={styles.label}>{live ? "Live" : state}</span>
        {live && received > 0 ? (
          <span className={styles.count} aria-label={`${received} events received`}>
            {received}
          </span>
        ) : null}
      </span>
    </Tooltip>
  );
}

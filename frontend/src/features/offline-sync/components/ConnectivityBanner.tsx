/**
 * Connectivity banner driven by the browser's online and offline events.
 */

import { CloudOff, RefreshCw, Wifi } from "lucide-react";
import { connectivityCopy } from "../sync";
import type { Connectivity } from "../types";
import styles from "./ConnectivityBanner.module.css";

/** Props accepted by {@link ConnectivityBanner}. */
export interface ConnectivityBannerProps {
  /** Current connectivity state. */
  connectivity: Connectivity;
  /** Number of mutations waiting in the queue. */
  pending: number;
  /** Optional action shown on the trailing edge. */
  onRetry?: () => void;
  /** Additional class applied to the banner. */
  className?: string;
}

/**
 * Render a prominent, announced banner describing connectivity.
 *
 * @param props - The component props.
 * @returns The banner element.
 */
export function ConnectivityBanner({
  connectivity,
  pending,
  onRetry,
  className,
}: ConnectivityBannerProps) {
  const online = connectivity === "online";
  const copy = connectivityCopy(online, pending);
  return (
    <div
      className={[styles.banner, styles[copy.tone], className].filter(Boolean).join(" ")}
      role="status"
      aria-live="polite"
      data-connectivity={connectivity}
    >
      <span className={styles.icon} aria-hidden="true">
        {online ? <Wifi size={18} /> : <CloudOff size={18} />}
      </span>
      <div className={styles.text}>
        <p className={styles.title}>{copy.title}</p>
        <p className={styles.detail}>{copy.detail}</p>
      </div>
      {onRetry && online ? (
        <button
          type="button"
          className={styles.retry}
          onClick={onRetry}
          aria-label="Refresh sync status"
        >
          <RefreshCw size={14} aria-hidden="true" />
          Refresh
        </button>
      ) : null}
    </div>
  );
}

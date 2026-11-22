/**
 * Banner announcing activity that arrived since the last visible load.
 */

import { ArrowUp, Bell, X } from "lucide-react";
import { Button } from "../../../components/ui";
import styles from "./LiveBanner.module.css";

/** Props accepted by {@link LiveBanner}. */
export interface LiveBannerProps {
  count: number;
  onShow: () => void;
  onDismiss: () => void;
}

/**
 * Render an aria-live banner when new events are available.
 *
 * @param props - The arrival count and actions.
 * @returns The banner element, or `null` when there is nothing to announce.
 */
export function LiveBanner({ count, onShow, onDismiss }: LiveBannerProps) {
  if (count <= 0) return null;
  return (
    <div className={styles.banner} role="status" aria-live="polite">
      <Bell size={15} aria-hidden="true" />
      <span className={styles.message}>
        {count} new {count === 1 ? "event" : "events"} since your last visit
      </span>
      <Button size="sm" icon={<ArrowUp size={13} />} onClick={onShow}>
        Show new events
      </Button>
      <button
        type="button"
        className={styles.dismiss}
        aria-label="Dismiss new events banner"
        onClick={onDismiss}
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

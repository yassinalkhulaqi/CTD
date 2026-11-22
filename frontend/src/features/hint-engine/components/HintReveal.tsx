/** Progressive reveal surface with a blurred preview for locked hints. */

import { Lock, Unlock } from "lucide-react";
import type { HintView } from "../types";
import styles from "./HintReveal.module.css";

/** Props accepted by {@link HintReveal}. */
export interface HintRevealProps {
  hint: HintView;
  compact?: boolean;
}

/**
 * Render the hint body, revealing it only after a successful unlock.
 *
 * @param props - The component props.
 * @returns The reveal surface.
 */
export function HintReveal({ hint, compact = false }: HintRevealProps) {
  return (
    <div
      className={`${styles.reveal} ${hint.unlocked ? styles.visible : styles.blurred} ${
        compact ? styles.compact : ""
      }`}
      data-state={hint.state}
    >
      <p className={styles.body} aria-hidden={!hint.unlocked}>
        {hint.content}
      </p>
      {!hint.unlocked ? (
        <div className={styles.veil}>
          <span className={styles.icon} aria-hidden="true">
            {hint.state === "exhausted" ? (
              <Lock size={16} />
            ) : (
              <Unlock size={16} />
            )}
          </span>
          <span className={styles.caption}>
            {hint.state === "exhausted" ? "Budget needed" : "Locked"}
          </span>
        </div>
      ) : null}
    </div>
  );
}

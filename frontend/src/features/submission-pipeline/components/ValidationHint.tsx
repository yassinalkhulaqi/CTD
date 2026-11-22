/**
 * Accessible summary of the rules applied to a submitted flag.
 */

import { AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import type { ValidationResult } from "../types";
import { VALIDATION_HINTS } from "../logic";
import styles from "./ValidationHint.module.css";

/** Props accepted by {@link ValidationHint}. */
export interface ValidationHintProps {
  /** Result of the most recent client-side validation. */
  result: ValidationResult | null;
  /** Configured rules, used to describe disabled checks. */
  rules: string[];
  /** Render the hints in a compact form. */
  compact?: boolean;
}

/**
 * Render validation guidance and the latest validation message.
 *
 * @param props - The component props.
 * @returns The hint panel.
 */
export function ValidationHint({
  result,
  rules,
  compact = false,
}: ValidationHintProps) {
  const active = rules.length > 0 ? rules : VALIDATION_HINTS;
  return (
    <div
      className={`${styles.panel} ${compact ? styles.compact : ""}`}
      aria-label="Flag validation guidance"
    >
      <p className={styles.heading}>
        <ShieldCheck size={14} aria-hidden="true" />
        Validation checks
      </p>
      {result ? (
        <p
          className={`${styles.message} ${result.valid ? styles.valid : styles.invalid}`}
          role={result.valid ? "status" : "alert"}
        >
          {result.valid ? (
            <CheckCircle2 size={15} aria-hidden="true" />
          ) : (
            <AlertCircle size={15} aria-hidden="true" />
          )}
          <span>{result.message}</span>
        </p>
      ) : null}
      <ul className={styles.list}>
        {active.map((hint) => (
          <li key={hint} className={styles.item}>
            {hint}
          </li>
        ))}
      </ul>
    </div>
  );
}

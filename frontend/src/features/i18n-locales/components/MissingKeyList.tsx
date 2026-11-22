/** List of reference keys that still need a translation. */

import { KeyRound } from "lucide-react";
import { Badge, EmptyState } from "../../../components/ui";
import styles from "./MissingKeyList.module.css";
import type { MissingKey } from "../types";

/** Props accepted by {@link MissingKeyList}. */
export interface MissingKeyListProps {
  /** The missing keys to display. */
  items: MissingKey[];
  /** The locale being inspected. */
  locale?: string;
}

/**
 * Render the missing translation keys as a compact list.
 *
 * @param props - The list props.
 * @returns The list or an empty state.
 */
export function MissingKeyList({ items, locale }: MissingKeyListProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Nothing missing"
        description={
          locale
            ? `${locale} covers every reference key.`
            : "The catalogue is complete."
        }
      />
    );
  }

  return (
    <div className={styles.wrapper}>
      <ul
        className={styles.list}
        aria-label={`Missing keys for ${locale ?? "catalogue"}`}
      >
        {items.map((item) => (
          <li key={item.qualified_key} className={styles.item}>
            <span className={styles.icon} aria-hidden="true">
              <KeyRound size={14} />
            </span>
            <div className={styles.body}>
              <span className={styles.key}>{item.qualified_key}</span>
              <span className={styles.reference}>{item.reference_value}</span>
            </div>
            {item.has_fallback ? (
              <Badge tone="warning">fallback: {item.resolved_locale}</Badge>
            ) : (
              <Badge tone="danger">no fallback</Badge>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

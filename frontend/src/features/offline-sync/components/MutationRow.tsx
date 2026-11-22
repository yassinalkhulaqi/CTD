/**
 * A single, keyboard operable row in the mutation queue.
 */

import { cn } from "../../lib/utils";
import { Badge } from "../../components/ui";
import { Pencil, Plus, Trash2 } from "lucide-react";
import {
  describeMutation,
  formatAge,
  formatAttempts,
  operationLabel,
  operationTone,
  payloadPreview,
  statusLabel,
  statusTone,
} from "../sync";
import type { PendingMutation } from "../types";
import styles from "./MutationRow.module.css";

/** Props accepted by {@link MutationRow}. */
export interface MutationRowProps {
  /** The mutation rendered by this row. */
  mutation: PendingMutation;
  /** Whether this row is currently selected. */
  selected?: boolean;
  /** Called when the row is activated. */
  onSelect?: (mutation: PendingMutation) => void;
  /** Additional class applied to the list item. */
  className?: string;
}

/**
 * Render one mutation as an accessible list item.
 *
 * @param props - The component props.
 * @returns The list item element.
 */
export function MutationRow({
  mutation,
  selected = false,
  onSelect,
  className,
}: MutationRowProps) {
  const operationIcon =
    mutation.operation === "create" ? (
      <Plus size={15} aria-hidden="true" />
    ) : mutation.operation === "delete" ? (
      <Trash2 size={15} aria-hidden="true" />
    ) : (
      <Pencil size={15} aria-hidden="true" />
    );

  return (
    <li className={cn(styles.item, className)}>
      <button
        type="button"
        className={cn(styles.row, selected && styles.selected)}
        onClick={() => onSelect?.(mutation)}
        aria-label={describeMutation(mutation)}
        aria-pressed={selected}
      >
        <span
          className={cn(
            styles.icon,
            styles[operationTone(mutation.operation)],
          )}
          aria-hidden="true"
        >
          {operationIcon}
        </span>
        <span className={styles.body}>
          <span className={styles.title}>
            {operationLabel(mutation.operation)} {mutation.entity_label}
            <span className={styles.identifier}>#{mutation.id.slice(-6)}</span>
          </span>
          <span className={styles.payload} title={JSON.stringify(mutation.payload)}>
            {payloadPreview(mutation.payload)}
          </span>
          {mutation.last_error ? (
            <span className={styles.error}>{mutation.last_error}</span>
          ) : null}
        </span>
        <span className={styles.meta}>
          <Badge tone={statusTone(mutation.status)} dot>
            {statusLabel(mutation.status)}
          </Badge>
          <span className={styles.detail}>
            v{mutation.base_version} · {formatAttempts(mutation.attempts)}
          </span>
          <span className={styles.time}>{formatAge(mutation.created_at)}</span>
        </span>
      </button>
    </li>
  );
}

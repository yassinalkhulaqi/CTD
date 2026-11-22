/**
 * The setup checklist panel.
 */

import { ListChecks } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Progress,
  Skeleton,
} from "../../../components/ui";
import { checklistSummary } from "../tour";
import type { Checklist } from "../types";
import { EmptyState } from "./EmptyState";
import styles from "./ChecklistPanel.module.css";

/** Props accepted by {@link ChecklistPanel}. */
export interface ChecklistPanelProps {
  /** The checklist to display, or null while loading. */
  checklist: Checklist | null;
  /** Called when an item checkbox is toggled. */
  onToggle: (itemId: string, done: boolean) => void;
  /** Identifier of an item with a mutation in flight. */
  busyItemId?: string | null;
  /** Show loading placeholders instead of content. */
  loading?: boolean;
}

/**
 * Render a progress checklist with optimistic, accessible checkboxes.
 *
 * @param props - The component props.
 * @returns The checklist panel.
 */
export function ChecklistPanel({
  checklist,
  onToggle,
  busyItemId = null,
  loading = false,
}: ChecklistPanelProps) {
  const items = checklist?.items ?? [];
  const summary = checklistSummary(items);

  return (
    <Card
      className={styles.panel}
      as="section"
      aria-labelledby="checklist-title"
    >
      <CardHeader>
        <CardTitle level={3} id="checklist-title">
          Setup checklist
        </CardTitle>
        <CardDescription>
          {summary.completed} of {summary.total} tasks complete
        </CardDescription>
      </CardHeader>
      <CardContent className={styles.content}>
        <Progress
          value={summary.percent}
          tone="success"
          label="Checklist completion"
          className={styles.progress}
        />
        {loading ? (
          <div className={styles.loading}>
            <Skeleton lines={4} />
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            variant="checklist"
            title="Nothing to tick yet"
            description="Your setup tasks will appear here as you explore the tour."
          />
        ) : (
          <ul className={styles.list}>
            {items.map((item) => (
              <li key={item.id} className={styles.item}>
                <label className={styles.label}>
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    checked={item.done}
                    disabled={busyItemId === item.id}
                    onChange={(event) =>
                      onToggle(item.id, event.target.checked)
                    }
                  />
                  <span className={styles.text}>
                    <span
                      className={
                        item.done ? styles.doneLabel : styles.itemLabel
                      }
                    >
                      {item.label}
                    </span>
                    {item.detail ? (
                      <span className={styles.detail}>{item.detail}</span>
                    ) : null}
                  </span>
                  <Badge tone={item.done ? "success" : "neutral"} outline>
                    {item.status}
                  </Badge>
                </label>
              </li>
            ))}
          </ul>
        )}
        {!loading && checklist ? (
          <p className={styles.footer}>
            <ListChecks size={14} aria-hidden="true" />
            Tick items manually or complete their linked tour step.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

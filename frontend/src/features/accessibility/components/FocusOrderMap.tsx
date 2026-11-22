import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Kbd,
} from "../../../components/ui";
import { createFocusTrap, currentFocus, focusAt, moveFocus } from "../a11y";
import type { FocusOrderEntry } from "../types";
import styles from "./FocusOrderMap.module.css";

export interface FocusOrderMapProps {
  entries: FocusOrderEntry[];
  onReorder?: (ids: string[]) => Promise<FocusOrderEntry[]>;
}

export function FocusOrderMap({ entries, onReorder }: FocusOrderMapProps) {
  const [trap, setTrap] = useState(() => createFocusTrap(entries));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTrap((current) => createFocusTrap(entries, current.index));
  }, [entries]);

  const current = currentFocus(trap);

  async function swap(index: number, offset: number): Promise<void> {
    const target = index + offset;
    if (target < 0 || target >= trap.entries.length) return;
    const ids = trap.entries.map((entry) => entry.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    const optimistic = ids
      .map((id, position) => {
        const entry = trap.entries.find((candidate) => candidate.id === id);
        return entry ? { ...entry, order: position + 1 } : null;
      })
      .filter((entry): entry is FocusOrderEntry => entry !== null);
    setTrap((state) => createFocusTrap(optimistic, state.index));
    setError(null);
    if (!onReorder) return;
    try {
      const saved = await onReorder(ids);
      setTrap((state) => createFocusTrap(saved, state.index));
    } catch (cause) {
      setTrap(createFocusTrap(entries));
      setError(
        cause instanceof Error ? cause.message : "Unable to save focus order",
      );
    }
  }

  return (
    <Card as="section" className={styles.card} aria-labelledby="focus-title">
      <CardHeader
        actions={<Badge tone="info">{trap.entries.length} stops</Badge>}
      >
        <CardTitle id="focus-title">Focus order map</CardTitle>
        <CardDescription>
          Step through the tab sequence with wrapping and inspect the current
          stop.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {trap.entries.length === 0 ? (
          <EmptyState
            title="No focus stops"
            description="Add focus entries to preview the trap state machine."
          />
        ) : (
          <>
            <ButtonGroup
              className={styles.controls}
              aria-label="Focus trap controls"
            >
              <Button
                size="sm"
                variant="secondary"
                icon={<span aria-hidden="true">←</span>}
                onClick={() => setTrap((state) => moveFocus(state, "previous"))}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="secondary"
                trailingIcon={<span aria-hidden="true">→</span>}
                onClick={() => setTrap((state) => moveFocus(state, "next"))}
              >
                Next
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  setTrap((state) => focusAt(state, state.entries[0].id))
                }
              >
                Reset
              </Button>
            </ButtonGroup>

            <ol className={styles.track}>
              {trap.entries.map((entry, index) => {
                const active = current?.id === entry.id;
                return (
                  <li className={styles.stop} key={entry.id}>
                    <button
                      type="button"
                      className={styles.stopButton}
                      data-active={active}
                      aria-current={active ? "step" : undefined}
                      tabIndex={active ? 0 : -1}
                      onClick={() =>
                        setTrap((state) => focusAt(state, entry.id))
                      }
                    >
                      <Kbd>{index + 1}</Kbd>
                      <span className={styles.stopLabel}>{entry.label}</span>
                      <span className={styles.stopAria}>
                        {entry.aria_label}
                      </span>
                    </button>
                    <div className={styles.reorder}>
                      <button
                        type="button"
                        className={styles.reorderButton}
                        aria-label={`Move ${entry.label} earlier`}
                        disabled={index === 0}
                        onClick={() => void swap(index, -1)}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className={styles.reorderButton}
                        aria-label={`Move ${entry.label} later`}
                        disabled={index === trap.entries.length - 1}
                        onClick={() => void swap(index, 1)}
                      >
                        ↓
                      </button>
                    </div>
                  </li>
                );
              })}
            </ol>

            <p className={styles.announcement} role="status" aria-live="polite">
              Current stop {trap.index + 1} of {trap.entries.length}:{" "}
              {current?.label}
            </p>
          </>
        )}
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

/**
 * Multi-select control for the event allowlist.
 */

import { Checkbox } from "../../../components/ui";
import { eventLabel } from "../logic";
import { ALL_EVENTS } from "../types";
import styles from "./EventSelector.module.css";

/** Props accepted by {@link EventSelector}. */
export interface EventSelectorProps {
  selected: string[];
  onChange: (events: string[]) => void;
  disabled?: boolean;
  error?: string;
  compact?: boolean;
}

/**
 * Render one checkbox per allowlisted event.
 *
 * @param props - The selector props.
 * @returns The event selector element.
 */
export function EventSelector({
  selected,
  onChange,
  disabled = false,
  error,
  compact = false,
}: EventSelectorProps) {
  const toggle = (event: string): void => {
    onChange(
      selected.includes(event)
        ? selected.filter((item) => item !== event)
        : [...selected, event],
    );
  };

  return (
    <fieldset className={styles.fieldset} disabled={disabled}>
      <legend className={styles.legend}>Subscribed events</legend>
      <div className={compact ? styles.gridCompact : styles.grid}>
        {ALL_EVENTS.map((event) => (
          <Checkbox
            key={event}
            checked={selected.includes(event)}
            onChange={() => toggle(event)}
            className={styles.option}
          >
            <span className={styles.optionText}>
              <span>{eventLabel(event)}</span>
              <code className={styles.eventName}>{event}</code>
            </span>
          </Checkbox>
        ))}
      </div>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

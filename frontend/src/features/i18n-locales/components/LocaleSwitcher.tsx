/** Accessible selector that switches the active locale. */

import { Globe2 } from "lucide-react";
import { Select } from "../../../components/ui";
import { DirectionBadge } from "./DirectionBadge";
import styles from "./LocaleSwitcher.module.css";
import type { Locale } from "../types";

/** Props accepted by {@link LocaleSwitcher}. */
export interface LocaleSwitcherProps {
  /** The registered locales. */
  locales: Locale[];
  /** The active locale code. */
  value: string;
  /** Called when a different locale is selected. */
  onChange: (code: string) => void;
  /** Disable the selector while data is loading. */
  disabled?: boolean;
  /** Override the accessible label of the selector. */
  label?: string;
}

/**
 * Render the language selector with direction and fallback details.
 *
 * @param props - The switcher props.
 * @returns The switcher element.
 */
export function LocaleSwitcher({
  locales,
  value,
  onChange,
  disabled = false,
  label = "Language",
}: LocaleSwitcherProps) {
  const active = locales.find((locale) => locale.code === value);
  const options = locales.map((locale) => ({
    value: locale.code,
    label: `${locale.name} (${locale.code})`,
  }));

  return (
    <div className={styles.switcher}>
      <div className={styles.control}>
        <Select
          label={label}
          value={value}
          options={options}
          disabled={disabled || locales.length === 0}
          placeholder={
            locales.length === 0 ? "No languages available" : undefined
          }
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      {active ? (
        <div className={styles.details} aria-live="polite">
          <Globe2 size={14} aria-hidden="true" />
          <DirectionBadge
            direction={active.direction}
            code={active.code}
            compact
          />
          <span className={styles.chain}>
            Fallback: {active.chain.join(" \u2192 ")}
          </span>
        </div>
      ) : null}
    </div>
  );
}

/** Keyboard accessible five-star rating control. */

import { useRef, useState, type KeyboardEvent } from "react";
import { Star } from "lucide-react";
import { cn } from "../../../lib/utils";
import styles from "./RatingStars.module.css";

/** Props accepted by {@link RatingStars}. */
export interface RatingStarsProps {
  /** The current member's rating, or zero when unrated. */
  value?: number;
  /** The average rating, shown when the control is read-only. */
  average?: number;
  /** Number of submitted ratings. */
  count?: number;
  /** Called when a score is committed. Omit for a read-only display. */
  onRate?: (score: number) => void;
  /** Disable interaction. */
  disabled?: boolean;
  /** Visual size of the stars. */
  size?: "sm" | "md" | "lg";
  /** Accessible group label. */
  label?: string;
  /** Additional class name. */
  className?: string;
}

const SCORES = [1, 2, 3, 4, 5];

/**
 * Render a star rating that can be operated with a pointer or keyboard.
 *
 * Arrow keys move between stars, Home and End jump to the ends, and Enter or
 * Space commits the focused score.
 *
 * @param props - The component props.
 * @returns The rating control.
 */
export function RatingStars({
  value = 0,
  average = 0,
  count = 0,
  onRate,
  disabled = false,
  size = "md",
  label = "Rate this writeup",
  className,
}: RatingStarsProps) {
  const [focused, setFocused] = useState(Math.min(4, Math.max(0, value - 1)));
  const [hovered, setHovered] = useState(0);
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const shown = hovered || value || Math.round(average);

  if (!onRate) {
    return (
      <span
        className={cn(styles.readOnly, styles[size], className)}
        role="img"
        aria-label={`${average.toFixed(1)} out of 5 from ${count} rating${count === 1 ? "" : "s"}`}
      >
        {SCORES.map((score) => (
          <Star
            key={score}
            size={size === "sm" ? 13 : size === "lg" ? 20 : 16}
            className={
              score <= Math.round(average) ? styles.filled : styles.empty
            }
            aria-hidden="true"
          />
        ))}
      </span>
    );
  }

  const commit = (score: number) => {
    if (disabled) return;
    onRate?.(score);
    setHovered(0);
  };

  const handleKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    if (disabled) return;
    let next = index;
    if (event.key === "ArrowRight" || event.key === "ArrowDown")
      next = Math.min(4, index + 1);
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp")
      next = Math.max(0, index - 1);
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = 4;
    else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      commit(index + 1);
      return;
    } else return;
    event.preventDefault();
    setFocused(next);
    buttons.current[next]?.focus();
  };

  return (
    <div
      className={cn(
        styles.group,
        styles[size],
        disabled && styles.disabled,
        className,
      )}
      role="radiogroup"
      aria-label={label}
      aria-disabled={disabled || undefined}
      onMouseLeave={() => setHovered(0)}
    >
      {SCORES.map((score, index) => (
        <button
          key={score}
          ref={(node) => {
            buttons.current[index] = node;
          }}
          type="button"
          role="radio"
          aria-checked={value === score}
          aria-label={`${score} star${score === 1 ? "" : "s"}`}
          tabIndex={focused === index ? 0 : -1}
          disabled={disabled}
          className={cn(styles.starButton, score <= shown && styles.activeStar)}
          onFocus={() => setFocused(index)}
          onMouseEnter={() => setHovered(score)}
          onClick={() => commit(score)}
          onKeyDown={(event) => handleKeyDown(event, index)}
        >
          <Star
            size={size === "sm" ? 13 : size === "lg" ? 20 : 16}
            aria-hidden="true"
          />
        </button>
      ))}
      {count > 0 ? <span className={styles.count}>{count}</span> : null}
    </div>
  );
}

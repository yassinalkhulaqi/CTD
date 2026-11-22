/**
 * Chip editor for note tags.
 */

import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";
import { IconButton, Input } from "../../../components/ui";
import { normaliseTags } from "../logic";
import styles from "./TagInput.module.css";

/** Props accepted by {@link TagInput}. */
export interface TagInputProps {
  /** The current tags. */
  tags: string[];
  /** Called when a tag is added. */
  onAdd: (tag: string) => void;
  /** Called when a tag is removed. */
  onRemove: (tag: string) => void;
  /** Whether the control is disabled. */
  disabled?: boolean;
}

/**
 * Render an input for adding tags and removable chips for existing ones.
 *
 * @param props - The component props.
 * @returns The tag input element.
 */
export function TagInput({
  tags,
  onAdd,
  onRemove,
  disabled = false,
}: TagInputProps) {
  const [value, setValue] = useState("");

  const commit = (): void => {
    const cleaned = normaliseTags([value]);
    if (cleaned.length > 0) onAdd(cleaned[0]);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.chips} aria-label="Note tags">
        {tags.map((tag) => (
          <span className={styles.chip} key={tag}>
            <span className={styles.hash} aria-hidden="true">
              #
            </span>
            {tag}
            <IconButton
              size="sm"
              variant="ghost"
              icon={<X size={11} />}
              label={`Remove tag ${tag}`}
              disabled={disabled}
              onClick={() => onRemove(tag)}
              className={styles.remove}
            />
          </span>
        ))}
      </div>
      <div className={styles.addRow}>
        <Input
          label="Add tag"
          hideLabel
          placeholder="Add a tag…"
          value={value}
          disabled={disabled}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
          className={styles.input}
        />
        <IconButton
          icon={<Plus size={14} />}
          label="Add tag"
          disabled={disabled || !value.trim()}
          onClick={commit}
        />
      </div>
    </div>
  );
}

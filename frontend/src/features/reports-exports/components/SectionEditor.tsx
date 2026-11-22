/**
 * Editor for one template section inside the report builder.
 */

import { ArrowDown, ArrowUp, Braces, GripVertical, Trash2 } from "lucide-react";
import {
  Badge,
  Checkbox,
  IconButton,
  Input,
  Select,
  Textarea,
} from "../../../components/ui";
import { KIND_LABELS, KIND_ORDER, placeholderTokens } from "../reportModel";
import type { SectionConfig, SectionKind, SectionPatch } from "../types";
import styles from "./SectionEditor.module.css";

/** Props accepted by {@link SectionEditor}. */
export interface SectionEditorProps {
  sections: SectionConfig[];
  onToggle: (id: string) => void;
  onPatch: (id: string, patch: SectionPatch) => void;
  onMove: (id: string, direction: -1 | 1) => void;
  onRemove: (id: string) => void;
  disabled?: boolean;
}

/**
 * Render the list of editable sections.
 *
 * @param props - The component props.
 * @returns The section editor element.
 */
export function SectionEditor({
  sections,
  onToggle,
  onPatch,
  onMove,
  onRemove,
  disabled = false,
}: SectionEditorProps) {
  if (sections.length === 0) {
    return (
      <p className={styles.empty} role="status">
        This template has no sections. Add one below to start building the
        report.
      </p>
    );
  }

  return (
    <ol className={styles.list} aria-label="Report sections">
      {sections.map((section, index) => {
        const tokens = placeholderTokens(
          `${section.title} ${section.body} ${section.source}`,
        );
        return (
          <li
            key={section.id}
            className={`${styles.item} ${section.enabled ? "" : styles.disabled}`}
          >
            <div className={styles.header}>
              <GripVertical
                size={14}
                className={styles.grip}
                aria-hidden="true"
              />
              <Checkbox
                checked={section.enabled}
                disabled={disabled}
                aria-label={`Include ${section.title}`}
                onChange={() => onToggle(section.id)}
              >
                Include
              </Checkbox>
              <span className={styles.position}>{index + 1}</span>
              <div
                className={styles.actions}
                role="group"
                aria-label={`Reorder ${section.title}`}
              >
                <IconButton
                  icon={<ArrowUp size={14} />}
                  label={`Move ${section.title} up`}
                  disabled={disabled || index === 0}
                  onClick={() => onMove(section.id, -1)}
                  size="sm"
                />
                <IconButton
                  icon={<ArrowDown size={14} />}
                  label={`Move ${section.title} down`}
                  disabled={disabled || index === sections.length - 1}
                  onClick={() => onMove(section.id, 1)}
                  size="sm"
                />
                <IconButton
                  icon={<Trash2 size={14} />}
                  label={`Remove ${section.title}`}
                  disabled={disabled}
                  onClick={() => onRemove(section.id)}
                  size="sm"
                  variant="ghost"
                />
              </div>
            </div>
            <div className={styles.grid}>
              <Input
                label="Section title"
                value={section.title}
                disabled={disabled}
                onChange={(event) =>
                  onPatch(section.id, { title: event.target.value })
                }
              />
              <Select
                label="Content type"
                value={section.kind}
                disabled={disabled}
                options={KIND_ORDER.map((kind) => ({
                  value: kind,
                  label: KIND_LABELS[kind],
                }))}
                onChange={(event) =>
                  onPatch(section.id, {
                    kind: event.target.value as SectionKind,
                  })
                }
              />
              <Input
                label="Data source"
                value={section.source}
                disabled={disabled}
                placeholder="e.g. challenges"
                hint="Key in the captured snapshot that supplies records."
                onChange={(event) =>
                  onPatch(section.id, { source: event.target.value })
                }
              />
              {section.kind === "table" ? (
                <Input
                  label="Columns"
                  value={section.columns.join(", ")}
                  disabled={disabled}
                  placeholder="title, points"
                  hint="Leave blank to infer columns from the data."
                  onChange={(event) =>
                    onPatch(section.id, {
                      columns: event.target.value
                        .split(",")
                        .map((column) => column.trim())
                        .filter(Boolean),
                    })
                  }
                />
              ) : null}
            </div>
            <Textarea
              label="Body"
              value={section.body}
              disabled={disabled}
              rows={2}
              placeholder="Use {{ team }} to insert a snapshot value."
              onChange={(event) =>
                onPatch(section.id, { body: event.target.value })
              }
            />
            {tokens.length > 0 ? (
              <div
                className={styles.tokens}
                aria-label="Placeholders used in this section"
              >
                <Braces size={12} aria-hidden="true" />
                {tokens.map((token) => (
                  <Badge key={token} tone="accent" outline>
                    {token}
                  </Badge>
                ))}
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

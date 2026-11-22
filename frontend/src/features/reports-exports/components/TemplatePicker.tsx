/**
 * Template selector for the report builder.
 */

import { FileText, Layers3 } from "lucide-react";
import { Badge, EmptyState, Select, Skeleton } from "../../../components/ui";
import type { ReportTemplate, TemplateScope } from "../types";
import styles from "./TemplatePicker.module.css";

/** Props accepted by {@link TemplatePicker}. */
export interface TemplatePickerProps {
  templates: ReportTemplate[];
  selectedId: string;
  onSelect: (template: ReportTemplate) => void;
  loading?: boolean;
  disabled?: boolean;
}

const SCOPE_LABELS: Record<TemplateScope, string> = {
  team: "Team",
  event: "Event",
  global: "Global",
};

/**
 * Render a labelled template dropdown with a short description.
 *
 * @param props - The component props.
 * @returns The picker element.
 */
export function TemplatePicker({
  templates,
  selectedId,
  onSelect,
  loading = false,
  disabled = false,
}: TemplatePickerProps) {
  const selected = templates.find((template) => template.id === selectedId);

  if (loading) {
    return (
      <div className={styles.picker} aria-busy="true">
        <Skeleton height={18} width={120} />
        <Skeleton height={38} />
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className={styles.picker}>
        <EmptyState
          icon={<Layers3 size={18} />}
          title="No templates yet"
          description="Templates define the sections of a report. Create one through the API to begin."
        />
      </div>
    );
  }

  return (
    <div className={styles.picker}>
      <Select
        label="Report template"
        hint="Changing the template reloads the builder sections."
        value={selectedId}
        disabled={disabled}
        options={templates.map((template) => ({
          value: template.id,
          label: template.name,
        }))}
        placeholder="Choose a template"
        onChange={(event) => {
          const template = templates.find(
            (item) => item.id === event.target.value,
          );
          if (template) onSelect(template);
        }}
      />
      {selected ? (
        <div className={styles.details}>
          <FileText size={14} aria-hidden="true" />
          <span className={styles.description}>{selected.description}</span>
          <Badge tone="info" outline>
            {SCOPE_LABELS[selected.scope]}
          </Badge>
          <Badge tone="neutral" outline>
            {selected.section_count} sections
          </Badge>
        </div>
      ) : null}
    </div>
  );
}

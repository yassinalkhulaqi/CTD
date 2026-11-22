/**
 * Template picker with inputs for each ``{{variable}}`` placeholder.
 */

import { useMemo, useState } from "react";
import { FilePlus2, LayoutTemplate } from "lucide-react";
import {
  Button,
  EmptyState,
  Input,
  Select,
  type SelectOption,
} from "../../../components/ui";
import { extractTemplateVariables } from "../logic";
import type { NoteTemplate } from "../types";
import styles from "./TemplatePicker.module.css";

/** Props accepted by {@link TemplatePicker}. */
export interface TemplatePickerProps {
  /** The available templates. */
  templates: NoteTemplate[];
  /** Called when the rendered template should be applied to the draft. */
  onApply: (template: NoteTemplate, variables: Record<string, string>) => void;
}

/**
 * Render the template picker.
 *
 * @param props - The component props.
 * @returns The template picker element.
 */
export function TemplatePicker({ templates, onApply }: TemplatePickerProps) {
  const [selectedId, setSelectedId] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});

  const options = useMemo<SelectOption[]>(
    () => [
      { value: "", label: "Choose a template…" },
      ...templates.map((template) => ({
        value: template.id,
        label: template.name,
      })),
    ],
    [templates],
  );

  const selected =
    templates.find((template) => template.id === selectedId) ?? null;
  const variables = selected ? extractTemplateVariables(selected.body) : [];

  const choose = (id: string): void => {
    setSelectedId(id);
    setValues({});
  };

  return (
    <section className={styles.picker} aria-label="Template picker">
      <div className={styles.heading}>
        <LayoutTemplate size={14} aria-hidden="true" />
        <span>Start from a template</span>
      </div>
      {templates.length === 0 ? (
        <EmptyState
          icon={<FilePlus2 size={18} />}
          title="No templates yet"
          description="Templates appear here once they are created through the API."
        />
      ) : (
        <>
          <Select
            label="Template"
            hideLabel
            options={options}
            value={selectedId}
            onChange={(event) => choose(event.target.value)}
          />
          {variables.length > 0 ? (
            <div className={styles.variables}>
              {variables.map((name) => (
                <Input
                  key={name}
                  label={name.replaceAll("_", " ")}
                  placeholder={`Enter ${name}`}
                  value={values[name] ?? ""}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [name]: event.target.value,
                    }))
                  }
                />
              ))}
            </div>
          ) : null}
          <Button
            size="sm"
            variant="secondary"
            disabled={!selected}
            onClick={() => {
              if (selected) onApply(selected, values);
            }}
          >
            Use template
          </Button>
        </>
      )}
    </section>
  );
}

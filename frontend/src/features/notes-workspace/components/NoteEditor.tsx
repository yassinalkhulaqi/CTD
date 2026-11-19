/**
 * The editing pane for a note: title, format, body, tags and actions.
 */

import { Pin, Save, Trash2 } from "lucide-react";
import {
  Button,
  IconButton,
  Input,
  Select,
  Textarea,
} from "../../../components/ui";
import type { SelectOption } from "../../../components/ui";
import type { NoteDraft, NoteFormat } from "../types";
import { TagInput } from "./TagInput";
import styles from "./NoteEditor.module.css";

/** Props accepted by {@link NoteEditor}. */
export interface NoteEditorProps {
  /** The draft being edited. */
  draft: NoteDraft;
  /** Called with the changed draft fields. */
  onChange: (patch: Partial<NoteDraft>) => void;
  /** Called when the save button is pressed. */
  onSave: () => void;
  /** Called when the pin button is pressed. */
  onPin: () => void;
  /** Called when the delete button is pressed. */
  onDelete: () => void;
  /** Whether the editor has no persisted note yet. */
  isNew?: boolean;
  /** Whether saving is in progress. */
  saving?: boolean;
  /** Validation message shown below the body. */
  error?: string | null;
}

const FORMAT_OPTIONS: SelectOption[] = [
  { value: "markdown", label: "Markdown" },
  { value: "plain", label: "Plain text" },
  { value: "code", label: "Code" },
];

/**
 * Render the note editor.
 *
 * @param props - The component props.
 * @returns The editor element.
 */
export function NoteEditor({
  draft,
  onChange,
  onSave,
  onPin,
  onDelete,
  isNew = false,
  saving = false,
  error,
}: NoteEditorProps) {
  return (
    <div className={styles.editor}>
      <div className={styles.fields}>
        <Input
          label="Title"
          placeholder="Give this note a clear title"
          value={draft.title}
          maxLength={200}
          onChange={(event) => onChange({ title: event.target.value })}
        />
        <Select
          label="Format"
          options={FORMAT_OPTIONS}
          value={draft.format}
          onChange={(event) =>
            onChange({ format: event.target.value as NoteFormat })
          }
        />
      </div>
      <Textarea
        label="Body"
        hint="Markdown is previewed live on the right."
        error={error ?? undefined}
        value={draft.body}
        rows={18}
        showCount
        maxLength={20_000}
        onChange={(event) => onChange({ body: event.target.value })}
        className={styles.body}
      />
      <TagInput
        tags={draft.tags}
        onAdd={(tag) => onChange({ tags: [...draft.tags, tag] })}
        onRemove={(tag) =>
          onChange({ tags: draft.tags.filter((item) => item !== tag) })
        }
      />
      <div className={styles.actions}>
        <Button
          icon={<Save size={14} />}
          loading={saving}
          onClick={onSave}
          loadingLabel="Saving"
        >
          {isNew ? "Create note" : "Save note"}
        </Button>
        {!isNew ? (
          <IconButton
            icon={<Pin size={14} />}
            label={draft.pinned ? "Unpin note" : "Pin note"}
            variant={draft.pinned ? "primary" : "secondary"}
            onClick={onPin}
          />
        ) : null}
        {!isNew ? (
          <IconButton
            icon={<Trash2 size={14} />}
            label="Delete note"
            variant="danger"
            onClick={onDelete}
          />
        ) : null}
      </div>
    </div>
  );
}

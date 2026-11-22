/** Editor for a single catalogue message. */

import { useMemo } from "react";
import { Save, Sparkles } from "lucide-react";
import { Badge, Button, Input, Select, Textarea } from "../../../components/ui";
import { extractPlaceholders, normalizeKey } from "../format";
import type { Locale, MessageDraft } from "../types";
import styles from "./MessageEditor.module.css";

/** Props accepted by {@link MessageEditor}. */
export interface MessageEditorProps {
  /** The locales available for the message. */
  locales: Locale[];
  /** The draft being edited. */
  draft: MessageDraft;
  /** Called whenever the draft changes. */
  onChange: (draft: MessageDraft) => void;
  /** Called when the draft is saved. */
  onSave: (draft: MessageDraft) => void;
  /** Disable the save button while a request is in flight. */
  saving?: boolean;
  /** An error returned by the server. */
  error?: string;
}

/**
 * Render a controlled message editor with placeholder detection.
 *
 * @param props - The editor props.
 * @returns The editor element.
 */
export function MessageEditor({
  locales,
  draft,
  onChange,
  onSave,
  saving = false,
  error,
}: MessageEditorProps) {
  const placeholders = useMemo(
    () => extractPlaceholders(draft.value),
    [draft.value],
  );
  const valid = Boolean(
    draft.locale && draft.namespace.trim() && draft.key.trim(),
  );
  const options = locales.map((locale) => ({
    value: locale.code,
    label: `${locale.name} (${locale.code})`,
  }));

  const update = (patch: Partial<MessageDraft>) =>
    onChange({ ...draft, ...patch });

  return (
    <form
      className={styles.editor}
      onSubmit={(event) => {
        event.preventDefault();
        if (valid) onSave(draft);
      }}
    >
      <div className={styles.grid}>
        <Select
          label="Locale"
          value={draft.locale}
          options={options}
          onChange={(event) => update({ locale: event.target.value })}
        />
        <Input
          label="Namespace"
          value={draft.namespace}
          placeholder="ui"
          onChange={(event) => update({ namespace: event.target.value })}
        />
        <Input
          label="Key"
          value={draft.key}
          placeholder="greeting"
          onChange={(event) =>
            update({ key: normalizeKey(event.target.value) })
          }
          hint="Use dots for plural variants, for example items.one."
        />
      </div>

      <Textarea
        label="Message"
        value={draft.value}
        rows={4}
        placeholder="Hello, {name}!"
        onChange={(event) => update({ value: event.target.value })}
        hint="Wrap placeholder names in braces to interpolate values."
      />

      <div className={styles.placeholders} aria-live="polite">
        <span className={styles.placeholderLabel}>
          <Sparkles size={13} aria-hidden="true" /> Placeholders
        </span>
        {placeholders.length === 0 ? (
          <span className={styles.none}>None detected</span>
        ) : (
          placeholders.map((name) => (
            <Badge key={name} tone="accent">
              {`{${name}}`}
            </Badge>
          ))
        )}
      </div>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          type="submit"
          icon={<Save size={14} />}
          loading={saving}
          disabled={!valid}
        >
          Save message
        </Button>
        <span
          className={styles.qualified}
        >{`${draft.namespace || "namespace"}:${draft.key || "key"}`}</span>
      </div>
    </form>
  );
}

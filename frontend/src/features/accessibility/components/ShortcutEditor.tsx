import { useState, type FormEvent } from "react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Kbd,
} from "../../../components/ui";
import {
  canonicalShortcut,
  displayShortcut,
  findShortcutConflicts,
} from "../a11y";
import type { Shortcut, ShortcutCreatePayload } from "../types";
import styles from "./ShortcutEditor.module.css";

export interface ShortcutEditorProps {
  shortcuts: Shortcut[];
  onRegister: (payload: ShortcutCreatePayload) => Promise<Shortcut>;
  onDelete?: (id: string) => Promise<void>;
}

function draftShortcut(
  keys: string,
  action: string,
  scope: string,
): Shortcut | null {
  try {
    const canonical = canonicalShortcut(keys);
    const cleanScope = scope.trim() || "global";
    return {
      id: "__draft__",
      keys: canonical,
      canonical_keys: canonical,
      display_keys: displayShortcut(keys),
      action: action.trim() || "Unnamed action",
      scope: cleanScope,
      is_global: ["global", "*", "all"].includes(cleanScope.toLowerCase()),
      is_chord: canonical.includes(" "),
    };
  } catch {
    return null;
  }
}

export function ShortcutEditor({
  shortcuts,
  onRegister,
  onDelete,
}: ShortcutEditorProps) {
  const [keys, setKeys] = useState("Ctrl+Shift+K");
  const [action, setAction] = useState("Open command palette");
  const [scope, setScope] = useState("global");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const draft = draftShortcut(keys, action, scope);
  const conflicts = draft
    ? findShortcutConflicts([...shortcuts, draft]).filter(
        (conflict) =>
          conflict.left_id === "__draft__" || conflict.right_id === "__draft__",
      )
    : [];

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setStatus(null);
    if (!draft) {
      setError("Use a shortcut such as Ctrl+K, Alt+Shift+M or g g.");
      return;
    }
    if (conflicts.length > 0) {
      setError(`Conflict: ${conflicts[0].description}`);
      return;
    }
    setBusy(true);
    try {
      const created = await onRegister({
        keys: draft.canonical_keys,
        action: draft.action,
        scope: draft.scope,
      });
      setStatus(`${created.display_keys} registered for ${created.action}.`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to register shortcut",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(shortcut: Shortcut): Promise<void> {
    if (!onDelete) return;
    setBusy(true);
    setError(null);
    try {
      await onDelete(shortcut.id);
      setStatus(`${shortcut.display_keys} removed.`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to remove shortcut",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="section" className={styles.card} aria-labelledby="shortcut-title">
      <CardHeader>
        <CardTitle id="shortcut-title">Shortcut editor</CardTitle>
        <CardDescription>
          Bindings are canonicalised and checked against the active scope before
          saving.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className={styles.form}
          onSubmit={(event) => void handleSubmit(event)}
        >
          <Input
            label="Keys"
            value={keys}
            maxLength={120}
            onChange={(event) => setKeys(event.target.value)}
            hint="Ctrl+K, Alt+Shift+M or a two-step chord"
            error={!draft ? "Enter a valid key sequence" : undefined}
          />
          <Input
            label="Action"
            value={action}
            maxLength={120}
            onChange={(event) => setAction(event.target.value)}
          />
          <Input
            label="Scope"
            value={scope}
            maxLength={60}
            onChange={(event) => setScope(event.target.value)}
            hint="global applies to every screen"
          />
          <div className={styles.preview} aria-live="polite">
            <span>Preview</span>
            {draft ? (
              <>
                <Kbd>{draft.display_keys}</Kbd>
                <span className={styles.previewAction}>{draft.action}</span>
              </>
            ) : (
              <span className={styles.muted}>Invalid shortcut</span>
            )}
          </div>
          {conflicts.length > 0 ? (
            <p className={styles.conflict} role="alert">
              {conflicts[0].description}
            </p>
          ) : null}
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}
          {status ? (
            <p className={styles.status} role="status">
              {status}
            </p>
          ) : null}
          <Button type="submit" loading={busy} loadingLabel="Registering…">
            Register shortcut
          </Button>
        </form>

        <div className={styles.listHeader}>
          <h3>Registered bindings</h3>
          <Badge tone="neutral">{shortcuts.length}</Badge>
        </div>
        {shortcuts.length === 0 ? (
          <EmptyState
            title="No shortcuts yet"
            description="Add a binding to see conflict detection in action."
          />
        ) : (
          <ul className={styles.list}>
            {shortcuts.map((shortcut) => (
              <li className={styles.item} key={shortcut.id}>
                <Kbd>{shortcut.display_keys}</Kbd>
                <div className={styles.itemText}>
                  <strong>{shortcut.action}</strong>
                  <span>
                    {shortcut.scope}
                    {shortcut.is_chord ? " · chord" : ""}
                  </span>
                </div>
                {onDelete ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={busy}
                    onClick={() => void handleDelete(shortcut)}
                    aria-label={`Remove ${shortcut.action}`}
                  >
                    Remove
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

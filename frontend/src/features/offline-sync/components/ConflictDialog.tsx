/**
 * Modal dialog for choosing how to settle a version conflict.
 */

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, GitMerge, ShieldCheck } from "lucide-react";
import { Badge, Button, Modal } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import {
  STRATEGY_OPTIONS,
  isValidStrategy,
  mergePreview,
  parseJsonObject,
  payloadPreview,
} from "../sync";
import type {
  ConflictStrategy,
  Payload,
  PendingMutation,
} from "../types";
import styles from "./ConflictDialog.module.css";

/** Props accepted by {@link ConflictDialog}. */
export interface ConflictDialogProps {
  /** The conflicting mutation, or `null` when none is selected. */
  mutation: PendingMutation | null;
  /** Whether the dialog should be visible. */
  open: boolean;
  /** Whether the resolution request is in flight. */
  busy?: boolean;
  /** Failure returned by the resolution request. */
  error?: string | null;
  /** Called when the dialog should close. */
  onClose: () => void;
  /** Called with the chosen strategy and payload snapshots. */
  onResolve: (
    mutationId: string,
    strategy: ConflictStrategy,
    note: string,
    remotePayload: Payload,
    basePayload: Payload,
  ) => Promise<boolean> | boolean;
}

/**
 * Render a conflict resolution dialog with a live merge preview.
 *
 * @param props - The component props.
 * @returns The modal element, or `null` when closed.
 */
export function ConflictDialog({
  mutation,
  open,
  busy = false,
  error = null,
  onClose,
  onResolve,
}: ConflictDialogProps) {
  const [strategy, setStrategy] = useState<ConflictStrategy>("merge");
  const [note, setNote] = useState("");
  const [remoteJson, setRemoteJson] = useState("{}");
  const [baseJson, setBaseJson] = useState("{}");
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    if (!mutation) return;
    setStrategy("merge");
    setNote("");
    setRemoteJson("{}");
    setBaseJson("{}");
    setParseError(null);
  }, [mutation]);

  const parsed = useMemo(() => {
    const remote = parseJsonObject(remoteJson);
    const base = parseJsonObject(baseJson);
    if (!remote.ok || !base.ok) return null;
    return { remote: remote.value, base: base.value };
  }, [baseJson, remoteJson]);

  const localPayload = mutation?.payload ?? {};
  const preview = parsed
    ? mergePreview(parsed.base, localPayload, parsed.remote, strategy)
    : null;

  const submit = async () => {
    if (!mutation || !parsed) {
      setParseError("Correct the JSON payloads before resolving.");
      return;
    }
    setParseError(null);
    await onResolve(
      mutation.id,
      strategy,
      note,
      parsed.remote,
      parsed.base,
    );
  };

  return (
    <Modal
      open={open && mutation !== null}
      onClose={onClose}
      title="Resolve version conflict"
      description={
        mutation
          ? `${mutation.entity_label} changed on the server after this offline edit.`
          : undefined
      }
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            icon={<ShieldCheck size={15} />}
            onClick={() => void submit()}
            loading={busy}
            loadingLabel="Resolving"
            disabled={!parsed}
          >
            Apply resolution
          </Button>
        </>
      }
    >
      <div className={styles.content}>
        <div className={styles.comparison}>
          <div className={styles.column}>
            <p className={styles.columnTitle}>Offline edit</p>
            <code className={styles.code}>{payloadPreview(localPayload, 180)}</code>
          </div>
          <div className={styles.column}>
            <p className={styles.columnTitle}>Current server version</p>
            <code className={styles.code}>
              {parsed ? payloadPreview(parsed.remote, 180) : "Invalid JSON"}
            </code>
          </div>
        </div>

        <fieldset className={styles.strategies}>
          <legend className={styles.legend}>Resolution strategy</legend>
          {STRATEGY_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={cn(
                styles.option,
                strategy === option.value && styles.optionActive,
              )}
            >
              <input
                type="radio"
                name="conflict-strategy"
                value={option.value}
                checked={strategy === option.value}
                onChange={() => {
                  if (isValidStrategy(option.value)) setStrategy(option.value);
                }}
              />
              <span className={styles.optionBody}>
                <span className={styles.optionLabel}>{option.label}</span>
                <span className={styles.optionHint}>{option.hint}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <div className={styles.payloads}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Server payload (JSON)</span>
            <textarea
              className={styles.textarea}
              value={remoteJson}
              onChange={(event) => setRemoteJson(event.target.value)}
              rows={4}
              spellCheck={false}
              aria-invalid={parseError ? true : undefined}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Original payload (JSON)</span>
            <textarea
              className={styles.textarea}
              value={baseJson}
              onChange={(event) => setBaseJson(event.target.value)}
              rows={4}
              spellCheck={false}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>Review note (optional)</span>
          <input
            className={styles.input}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={500}
            placeholder="Why did you choose this strategy?"
          />
        </label>

        {parseError || error || !parsed ? (
          <p className={styles.error} role="alert">
            <AlertTriangle size={13} aria-hidden="true" />
            {parseError ?? error ?? "Enter valid JSON objects to preview the resolution."}
          </p>
        ) : null}

        {preview ? (
          <div className={styles.preview} aria-live="polite">
            <div className={styles.previewHeader}>
              <span className={styles.previewTitle}>
                <GitMerge size={14} aria-hidden="true" />
                Resolved payload preview
              </span>
              <Badge tone={preview.contested.length ? "warning" : "success"}>
                {preview.contested.length
                  ? `${preview.contested.length} contested`
                  : "clean merge"}
              </Badge>
            </div>
            <code className={styles.code}>{payloadPreview(preview.payload, 240)}</code>
            {preview.contested.length ? (
              <p className={styles.contested}>
                Both sides edited: {preview.contested.join(", ")}. The local value is kept.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

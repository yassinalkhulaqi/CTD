/** Accessible confirmation dialog for spending hint budget. */

import { useCallback, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Coins } from "lucide-react";
import { Button } from "../../../components/ui";
import { formatCredits } from "../hints";
import type { HintBudget, HintView } from "../types";
import styles from "./UnlockDialog.module.css";

/** Props accepted by {@link UnlockDialog}. */
export interface UnlockDialogProps {
  open: boolean;
  hint: HintView | null;
  budget: HintBudget | null;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Render a modal that traps focus, closes on Escape and restores focus.
 *
 * @param props - The component props.
 * @returns The dialog portal, or `null` while closed.
 */
export function UnlockDialog({
  open,
  hint,
  budget,
  busy = false,
  error = null,
  onConfirm,
  onClose,
}: UnlockDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const titleId = useId();
  const descriptionId = useId();

  const close = useCallback(() => closeRef.current(), []);

  useEffect(() => {
    if (!open || typeof document === "undefined") return;
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusables = (): HTMLElement[] => {
      const panel = panelRef.current;
      if (!panel) return [];
      return Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (element) => !element.hasAttribute("disabled"),
      );
    };
    focusables()[0]?.focus();

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus?.();
    };
  }, [open, close]);

  if (!open || !hint) return null;

  const remaining = budget ? Math.max(0, budget.remaining - hint.cost) : 0;

  return createPortal(
    <div
      className={styles.backdrop}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div
        ref={panelRef}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <span className={styles.kicker}>Tier {hint.tier} hint</span>
        <h2 id={titleId} className={styles.title}>
          Unlock “{hint.title}”?
        </h2>
        <p id={descriptionId} className={styles.description}>
          The full text is revealed to every member of your team and the cost is
          debited from the shared budget.
        </p>
        <dl className={styles.summary}>
          <div>
            <dt>Hint cost</dt>
            <dd>{formatCredits(hint.cost)} credits</dd>
          </div>
          <div>
            <dt>Budget after</dt>
            <dd>{formatCredits(remaining)} credits</dd>
          </div>
        </dl>
        {error ? (
          <p className={styles.error} role="alert">
            <AlertTriangle size={14} aria-hidden="true" />
            {error}
          </p>
        ) : null}
        <div className={styles.actions}>
          <Button variant="ghost" onClick={close} disabled={busy}>
            Cancel
          </Button>
          <Button
            icon={<Coins size={15} />}
            onClick={onConfirm}
            loading={busy}
            loadingLabel="Unlocking"
          >
            Unlock hint
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

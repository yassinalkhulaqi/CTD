/**
 * A secret input that never reveals stored plaintext secrets.
 */

import { useState } from "react";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { Button, Input } from "../../../components/ui";
import styles from "./SecretField.module.css";

/** Props accepted by {@link SecretField}. */
export interface SecretFieldProps {
  value: string;
  onChange?: (value: string) => void;
  label?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
  configured?: boolean;
}

/**
 * Render a password field with a keyboard operable reveal toggle.
 *
 * @param props - The field props.
 * @returns The secret field element.
 */
export function SecretField({
  value,
  onChange,
  label = "Signing secret",
  hint,
  error,
  disabled = false,
  configured = false,
}: SecretFieldProps) {
  const [revealed, setRevealed] = useState(false);
  return (
    <div className={styles.wrapper}>
      <Input
        label={label}
        type={revealed ? "text" : "password"}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
        disabled={disabled}
        hint={hint}
        error={error}
        icon={<KeyRound size={14} aria-hidden="true" />}
        autoComplete="new-password"
        spellCheck={false}
      />
      <Button
        className={styles.reveal}
        variant="ghost"
        size="sm"
        aria-label={revealed ? "Hide secret" : "Reveal secret"}
        aria-pressed={revealed}
        disabled={disabled}
        onClick={() => setRevealed((current) => !current)}
      >
        {revealed ? (
          <EyeOff size={15} aria-hidden="true" />
        ) : (
          <Eye size={15} aria-hidden="true" />
        )}
      </Button>
      {configured ? (
        <p className={styles.note}>
          Only a one-way digest is stored; the plaintext cannot be recovered.
        </p>
      ) : null}
    </div>
  );
}

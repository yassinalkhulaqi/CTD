/**
 * Button primitives: the primary interaction element of the design system.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";
import styles from "./Button.module.css";

/** The visual variants supported by the button. */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "subtle";

/** The size scale of the button. */
export type ButtonSize = "sm" | "md" | "lg";

/** Props accepted by {@link Button}. */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** The visual variant. */
  variant?: ButtonVariant;
  /** The size of the button. */
  size?: ButtonSize;
  /** Show a spinner and disable interaction. */
  loading?: boolean;
  /** Stretch the button to the width of its container. */
  block?: boolean;
  /** Render the leading icon. */
  icon?: ReactNode;
  /** Render the trailing icon. */
  trailingIcon?: ReactNode;
  /** Accessible label announced while the button is loading. */
  loadingLabel?: string;
}

/**
 * Render a button with the dashboard visual language.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The button element.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    block = false,
    icon,
    trailingIcon,
    loadingLabel = "Loading",
    className,
    children,
    disabled,
    type = "button",
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        styles.button,
        styles[variant],
        styles[size],
        block && styles.block,
        loading && styles.loading,
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-live={loading ? "polite" : undefined}
      {...rest}
    >
      {loading ? (
        <Loader2 className={styles.spinner} size={16} aria-hidden="true" />
      ) : icon ? (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span className={styles.label}>{loading ? loadingLabel : children}</span>
      {!loading && trailingIcon ? (
        <span className={styles.trailingIcon} aria-hidden="true">
          {trailingIcon}
        </span>
      ) : null}
    </button>
  );
});

/** Props accepted by {@link IconButton}. */
export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  /** The visual variant. */
  variant?: ButtonVariant;
  /** The size of the button. */
  size?: ButtonSize;
  /** Show a spinner and disable interaction. */
  loading?: boolean;
  /** The icon rendered inside the button. */
  icon: ReactNode;
  /** Required accessible label. */
  label: string;
}

/**
 * Render a square button holding a single icon.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The button element.
 */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { variant = "ghost", size = "md", loading = false, icon, label, className, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cn(styles.button, styles.iconButton, styles[variant], styles[size], className)}
      disabled={disabled || loading}
      aria-label={label}
      aria-busy={loading || undefined}
      title={label}
      {...rest}
    >
      {loading ? <Loader2 className={styles.spinner} size={16} aria-hidden="true" /> : icon}
    </button>
  );
});

/** Props accepted by {@link ButtonGroup}. */
export interface ButtonGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Join the buttons into a single visual control. */
  attached?: boolean;
}

/**
 * Group related buttons together.
 *
 * @param props - The component props.
 * @returns The group element.
 */
export function ButtonGroup({ attached = false, className, children, ...rest }: ButtonGroupProps) {
  return (
    <div
      className={cn(styles.group, attached && styles.groupAttached, className)}
      role="group"
      {...rest}
    >
      {children}
    </div>
  );
}

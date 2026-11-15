/**
 * Form field primitives: inputs, selects, textareas and toggles.
 */

import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";
import styles from "./Field.module.css";

/**
 * Join the optional ids referenced by a control.
 *
 * @param ids - The identifiers to join.
 * @returns The space separated identifier list, or `undefined`.
 */
function joinIds(...ids: Array<string | undefined>): string | undefined {
  const filtered = ids.filter((id): id is string => Boolean(id));
  return filtered.length > 0 ? filtered.join(" ") : undefined;
}

/** The height rhythm shared by the single-line controls. */
export type ControlSize = "sm" | "md" | "lg";

/** Props shared by every form control. */
export interface FieldBaseProps {
  /** The visible label of the control. */
  label?: string;
  /** Helper text rendered below the control. */
  hint?: string;
  /** Error message rendered below the control. */
  error?: string;
  /** Visually hide the label while keeping it accessible. */
  hideLabel?: boolean;
  /** Render the control in the disabled state. */
  disabled?: boolean;
  /** Additional class applied to the wrapper. */
  className?: string;
}

/**
 * Pick the size modifier for a control.
 *
 * @param size - The requested size.
 * @returns The CSS module class, or `undefined` for the default.
 */
function sizeClass(size: ControlSize | undefined): string | undefined {
  if (size === "sm") return styles.controlSm;
  if (size === "lg") return styles.controlLg;
  return undefined;
}

/** Props accepted by {@link Input}. */
export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "className">, FieldBaseProps {
  /** Icon rendered inside the leading edge of the control. */
  icon?: ReactNode;
  /** Content rendered inside the trailing edge of the control. */
  trailing?: ReactNode;
  /** The control height. */
  controlSize?: ControlSize;
}

/**
 * Render a labelled text input.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The form control.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    hint,
    error,
    hideLabel,
    disabled,
    className,
    icon,
    trailing,
    controlSize,
    id,
    ...rest
  },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className={cn(styles.field, error && styles.fieldInvalid, className)}>
      {label ? (
        <label className={cn(styles.label, hideLabel && styles.visuallyHidden)} htmlFor={inputId}>
          {label}
        </label>
      ) : null}
      <div className={styles.control}>
        {icon ? (
          <span className={styles.controlIcon} aria-hidden="true">
            {icon}
          </span>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            styles.input,
            icon && styles.inputWithIcon,
            trailing && styles.inputWithTrailing,
            sizeClass(controlSize),
            error && styles.inputInvalid,
          )}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={joinIds(hintId, errorId)}
          {...rest}
        />
        {trailing ? <span className={styles.trailing}>{trailing}</span> : null}
      </div>
      {error ? (
        <p className={styles.error} id={errorId} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint} id={hintId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});

/** Props accepted by {@link Textarea}. */
export interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "className">,
    FieldBaseProps {
  /** Show the character counter. */
  showCount?: boolean;
}

/**
 * Render a labelled textarea.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The form control.
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, error, hideLabel, disabled, className, showCount, id, value, maxLength, ...rest },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const length = typeof value === "string" ? value.length : 0;

  return (
    <div className={cn(styles.field, error && styles.fieldInvalid, className)}>
      <div className={styles.labelRow}>
        {label ? (
          <label className={cn(styles.label, hideLabel && styles.visuallyHidden)} htmlFor={inputId}>
            {label}
          </label>
        ) : null}
        {showCount && maxLength ? (
          <span className={styles.counter}>
            {length}/{maxLength}
          </span>
        ) : null}
      </div>
      <textarea
        ref={ref}
        id={inputId}
        className={cn(styles.textarea, error && styles.inputInvalid)}
        disabled={disabled}
        value={value}
        maxLength={maxLength}
        aria-invalid={error ? true : undefined}
        aria-describedby={joinIds(hintId, errorId)}
        {...rest}
      />
      {error ? (
        <p className={styles.error} id={errorId} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint} id={hintId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});

/** An option rendered by the {@link Select} component. */
export interface SelectOption {
  /** The value submitted with the form. */
  value: string;
  /** The label shown to the user. */
  label: string;
  /** Whether the option is disabled. */
  disabled?: boolean;
}

/** Props accepted by {@link Select}. */
export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "className" | "children">,
    FieldBaseProps {
  /** The available options. */
  options: SelectOption[];
  /** Render a placeholder option as the first entry. */
  placeholder?: string;
  /** The control height. */
  controlSize?: ControlSize;
}

/**
 * Render a styled native select.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The form control.
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  {
    label,
    hint,
    error,
    hideLabel,
    disabled,
    className,
    options,
    placeholder,
    controlSize,
    id,
    ...rest
  },
  ref,
) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div className={cn(styles.field, error && styles.fieldInvalid, className)}>
      {label ? (
        <label className={cn(styles.label, hideLabel && styles.visuallyHidden)} htmlFor={selectId}>
          {label}
        </label>
      ) : null}
      <div className={styles.control}>
        <select
          ref={ref}
          id={selectId}
          className={cn(styles.select, sizeClass(controlSize), error && styles.inputInvalid)}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={joinIds(hintId, errorId)}
          {...rest}
        >
          {placeholder ? (
            <option value="" disabled>
              {placeholder}
            </option>
          ) : null}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className={styles.selectIcon} size={15} aria-hidden="true" />
      </div>
      {error ? (
        <p className={styles.error} id={errorId} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint} id={hintId}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});

/** Props accepted by {@link Checkbox}. */
export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className">,
    FieldBaseProps {
  /** The visible label of the checkbox. */
  children?: ReactNode;
}

/**
 * Render an accessible checkbox with an animated tick.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The form control.
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, hint, error, hideLabel, disabled, className, children, id, ...rest },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  return (
    <div className={cn(styles.checkboxField, className)}>
      <label className={cn(styles.checkboxLabel, hideLabel && styles.visuallyHidden)} htmlFor={inputId}>
        <input
          ref={ref}
          id={inputId}
          type="checkbox"
          className={styles.checkboxInput}
          disabled={disabled}
          {...rest}
        />
        <span className={styles.checkboxBox} aria-hidden="true">
          <Check size={12} strokeWidth={3} />
        </span>
        <span className={styles.checkboxText}>{children ?? label}</span>
      </label>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint}>{hint}</p>
      ) : null}
    </div>
  );
});

/** Props accepted by {@link Switch}. */
export interface SwitchProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className">,
    FieldBaseProps {
  /** The visible label of the switch. */
  children?: ReactNode;
}

/**
 * Render an accessible toggle switch.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The form control.
 */
export const Switch = forwardRef<HTMLInputElement, SwitchProps>(function Switch(
  { label, hint, error, hideLabel, disabled, className, children, id, ...rest },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  return (
    <div className={cn(styles.switchField, className)}>
      <label className={cn(styles.switchLabel, hideLabel && styles.visuallyHidden)} htmlFor={inputId}>
        <input
          ref={ref}
          id={inputId}
          type="checkbox"
          role="switch"
          className={styles.switchInput}
          disabled={disabled}
          {...rest}
        />
        <span className={styles.switchTrack} aria-hidden="true">
          <span className={styles.switchThumb} />
        </span>
        <span className={styles.switchText}>{children ?? label}</span>
      </label>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className={styles.hint}>{hint}</p>
      ) : null}
    </div>
  );
});

/** Props accepted by {@link FormRow}. */
export interface FormRowProps {
  /** The row heading. */
  title: string;
  /** Supporting copy explaining the setting. */
  description?: string;
  /** The control rendered on the trailing edge. */
  children: ReactNode;
  /** Associate the heading with a control id. */
  htmlFor?: string;
  /** Additional class applied to the row. */
  className?: string;
}

/**
 * Render a settings row with a title, description and trailing control.
 *
 * @param props - The component props.
 * @returns The row element.
 */
export function FormRow({
  title,
  description,
  children,
  htmlFor,
  className,
}: FormRowProps) {
  return (
    <div className={cn(styles.formRow, className)}>
      <div className={styles.formRowText}>
        {htmlFor ? (
          <label className={styles.formRowTitle} htmlFor={htmlFor}>
            {title}
          </label>
        ) : (
          <span className={styles.formRowTitle}>{title}</span>
        )}
        {description ? <span className={styles.formRowDescription}>{description}</span> : null}
      </div>
      <div className={styles.formRowControl}>{children}</div>
    </div>
  );
}

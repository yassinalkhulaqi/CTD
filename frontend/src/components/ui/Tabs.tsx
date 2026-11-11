/**
 * Navigation primitives: tabs and segmented controls.
 */

import {
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "../../lib/utils";
import styles from "./Tabs.module.css";

interface TabsContextValue {
  value: string;
  setValue: (next: string) => void;
  baseId: string;
  variant: "underline" | "pill";
  label: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

/**
 * Read the surrounding tabs context.
 *
 * @returns The tabs context.
 * @throws When used outside of a {@link Tabs} component.
 */
export function useTabs(): TabsContextValue {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error("useTabs must be used inside a <Tabs> component");
  }
  return context;
}

/** Props accepted by {@link Tabs}. */
export interface TabsProps extends Omit<HTMLAttributes<HTMLDivElement>, "onChange"> {
  /** The identifier of the active tab. */
  value: string;
  /** Called when the active tab changes. */
  onValueChange: (value: string) => void;
  /** The tab panels. */
  children: ReactNode;
  /** The visual variant of the tab list. */
  variant?: "underline" | "pill";
  /** Accessible label of the tab list. */
  label?: string;
}

/**
 * Render a tabbed interface.
 *
 * @param props - The component props.
 * @returns The tabs element.
 */
export function Tabs({
  value,
  onValueChange,
  children,
  variant = "underline",
  label = "Tabs",
  className,
  ...rest
}: TabsProps) {
  const baseId = useId();
  const context = useMemo<TabsContextValue>(
    () => ({ value, setValue: onValueChange, baseId, variant, label }),
    [value, onValueChange, baseId, variant, label],
  );

  return (
    <TabsContext.Provider value={context}>
      <div className={cn(styles.tabs, className)} {...rest}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

/** Props accepted by {@link TabsList}. */
export interface TabsListProps extends HTMLAttributes<HTMLDivElement> {
  /** Scroll the list horizontally on overflow. */
  scrollable?: boolean;
}

/**
 * Render the list of tab triggers.
 *
 * @param props - The component props.
 * @returns The tab list element.
 */
export function TabsList({ scrollable = false, className, children, ...rest }: TabsListProps) {
  const context = useTabs();
  return (
    <div
      className={cn(styles.list, scrollable && styles.listScrollable, className)}
      role="tablist"
      aria-label={rest["aria-label"] ?? context.label}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Props accepted by {@link TabsTrigger}. */
export interface TabsTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  /** The identifier of the tab this trigger controls. */
  value: string;
  /** The label of the tab. */
  children: ReactNode;
  /** A small badge rendered after the label. */
  badge?: ReactNode;
  /** Disable the trigger. */
  disabled?: boolean;
}

/**
 * Render a single tab trigger.
 *
 * @param props - The component props.
 * @returns The trigger element.
 */
export function TabsTrigger({
  value,
  children,
  badge,
  disabled = false,
  className,
  onClick,
  ...rest
}: TabsTriggerProps) {
  const context = useTabs();
  const active = context.value === value;

  return (
    <button
      type="button"
      role="tab"
      id={`${context.baseId}-tab-${value}`}
      aria-selected={active}
      aria-controls={`${context.baseId}-panel-${value}`}
      tabIndex={active ? 0 : -1}
      disabled={disabled}
      className={cn(
        styles.trigger,
        context.variant === "pill" ? styles.triggerPill : styles.triggerUnderline,
        active && styles.triggerActive,
        className,
      )}
      onClick={(event) => {
        context.setValue(value);
        onClick?.(event);
      }}
      {...rest}
    >
      <span>{children}</span>
      {badge !== undefined && badge !== null ? (
        <span className={styles.triggerBadge}>{badge}</span>
      ) : null}
    </button>
  );
}

/** Props accepted by {@link TabsContent}. */
export interface TabsContentProps extends HTMLAttributes<HTMLDivElement> {
  /** The identifier of the tab this panel belongs to. */
  value: string;
  /** Keep the panel mounted while it is inactive. */
  keepMounted?: boolean;
}

/**
 * Render the panel associated with a tab.
 *
 * @param props - The component props.
 * @returns The panel element, or `null` when inactive.
 */
export function TabsContent({
  value,
  keepMounted = false,
  className,
  children,
  ...rest
}: TabsContentProps) {
  const context = useTabs();
  const active = context.value === value;

  if (!active && !keepMounted) return null;

  return (
    <div
      role="tabpanel"
      id={`${context.baseId}-panel-${value}`}
      aria-labelledby={`${context.baseId}-tab-${value}`}
      hidden={!active}
      className={cn(styles.panel, className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** An option rendered by the {@link SegmentedControl}. */
export interface SegmentOption<T extends string = string> {
  /** The value of the option. */
  value: T;
  /** The label of the option. */
  label: string;
  /** Optional icon rendered before the label. */
  icon?: ReactNode;
}

/** Props accepted by {@link SegmentedControl}. */
export interface SegmentedControlProps<T extends string = string> {
  /** The available options. */
  options: SegmentOption<T>[];
  /** The currently selected option. */
  value: T;
  /** Called when the selection changes. */
  onValueChange: (value: T) => void;
  /** Accessible label of the control. */
  label?: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a segmented control used to switch between views.
 *
 * @param props - The component props.
 * @returns The control element.
 */
export function SegmentedControl<T extends string = string>({
  options,
  value,
  onValueChange,
  label = "View",
  className,
}: SegmentedControlProps<T>) {
  const move = useCallback(
    (direction: number) => {
      const current = Math.max(
        0,
        options.findIndex((option) => option.value === value),
      );
      const next = (current + direction + options.length) % options.length;
      onValueChange(options[next].value);
    },
    [onValueChange, options, value],
  );

  return (
    <div className={cn(styles.segmented, className)} role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={cn(styles.segment, option.value === value && styles.segmentActive)}
          aria-pressed={option.value === value}
          tabIndex={option.value === value ? 0 : -1}
          onClick={() => {
            onValueChange(option.value);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") {
              event.preventDefault();
              move(1);
            } else if (event.key === "ArrowLeft") {
              event.preventDefault();
              move(-1);
            }
          }}
        >
          {option.icon ? (
            <span className={styles.segmentIcon} aria-hidden="true">
              {option.icon}
            </span>
          ) : null}
          {option.label}
        </button>
      ))}
    </div>
  );
}

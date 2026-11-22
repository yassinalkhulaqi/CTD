/**
 * Small display primitives: badges, avatars, status dots and keyboard keys.
 */

import { forwardRef, type CSSProperties, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import styles from "./Display.module.css";

/** The semantic variants available to a badge. */
export type BadgeTone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

/** Props accepted by {@link Badge}. */
export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** The semantic tone of the badge. */
  tone?: BadgeTone;
  /** Render a leading dot indicator. */
  dot?: boolean;
  /** Render the badge with a subtle outline instead of a fill. */
  outline?: boolean;
  /** Render the badge with a pulsing animation. */
  pulse?: boolean;
  /** The compact size variant. */
  size?: "sm" | "md";
}

/**
 * Render a compact status label.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The badge element.
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  {
    tone = "neutral",
    dot = false,
    outline = false,
    pulse = false,
    size = "md",
    className,
    children,
    ...rest
  },
  ref,
) {
  return (
    <span
      ref={ref}
      className={cn(
        styles.badge,
        styles[`badge-${tone}`],
        size === "sm" && styles["badge-sm"],
        outline && styles.outline,
        pulse && styles.pulse,
        className,
      )}
      {...rest}
    >
      {dot ? <span className={styles.badgeDot} aria-hidden="true" /> : null}
      {children}
    </span>
  );
});

/** Props accepted by {@link Avatar}. */
export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  /** The full name used to derive the initials. */
  name: string;
  /** An explicit image source. */
  src?: string;
  /** The size of the avatar. */
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  /** Render the presence indicator. */
  presence?: "online" | "away" | "offline";
  /** Override the derived accent colour. */
  color?: string;
}

/**
 * Derive up to two initials from a display name.
 *
 * @param name - The display name.
 * @returns The initials.
 */
export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Derive a stable accent colour from a string.
 *
 * @param value - The seed value.
 * @returns A hex colour.
 */
export function colorOf(value: string): string {
  const palette = [
    "#6366f1",
    "#22d3ee",
    "#f43f5e",
    "#a855f7",
    "#f59e0b",
    "#34d399",
    "#60a5fa",
    "#fb7185",
  ];
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return palette[hash % palette.length];
}

/**
 * Render a user or team avatar.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The avatar element.
 */
export const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(function Avatar(
  { name, src, size = "md", presence, color, className, style, ...rest },
  ref,
) {
  const accent = color ?? colorOf(name);
  return (
    <span
      ref={ref}
      className={cn(styles.avatar, styles[`avatar-${size}`], className)}
      style={{ ...style, "--avatar-accent": accent } as CSSProperties}
      title={name}
      {...rest}
    >
      {src ? (
        <img className={styles.avatarImage} src={src} alt="" loading="lazy" />
      ) : (
        <span className={styles.avatarInitials} aria-hidden="true">
          {initialsOf(name)}
        </span>
      )}
      {presence ? (
        <span
          className={cn(styles.presence, styles[`presence-${presence}`])}
          aria-label={`${name} is ${presence}`}
          role="img"
        />
      ) : null}
    </span>
  );
});

/** Props accepted by {@link AvatarGroup}. */
export interface AvatarGroupProps extends HTMLAttributes<HTMLDivElement> {
  /** The maximum number of avatars rendered before the overflow counter. */
  max?: number;
  /** The children rendered as avatars. */
  children: ReactNode;
  /** The number of hidden members, used for the overflow counter. */
  overflowCount?: number;
}

/**
 * Render a stacked group of avatars.
 *
 * @param props - The component props.
 * @returns The group element.
 */
export function AvatarGroup({
  max = 4,
  children,
  overflowCount = 0,
  className,
  ...rest
}: AvatarGroupProps) {
  const items = Array.isArray(children) ? children : [children];
  const visible = items.slice(0, max);
  const hidden = items.length - visible.length + overflowCount;

  return (
    <div className={cn(styles.avatarGroup, className)} {...rest}>
      {visible.map((child, index) => (
        <span className={styles.avatarStack} key={index}>
          {child}
        </span>
      ))}
      {hidden > 0 ? <span className={cn(styles.avatar, styles["avatar-sm"], styles.avatarOverflow)}>+{hidden}</span> : null}
    </div>
  );
}

/**
 * Render a keyboard shortcut.
 *
 * @param props - The component props.
 * @returns The key element.
 */
export function Kbd({ className, children, ...rest }: HTMLAttributes<HTMLElement>) {
  return (
    <kbd className={cn(styles.kbd, className)} {...rest}>
      {children}
    </kbd>
  );
}

/**
 * Render a small coloured dot used for status indicators.
 *
 * Without a `label` the dot is decorative; with one it is announced.
 *
 * @param props - The component props.
 * @returns The dot element.
 */
export function StatusDot({
  tone = "neutral",
  pulse = false,
  label,
  className,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone; pulse?: boolean; label?: string }) {
  return (
    <span
      className={cn(styles.statusDot, styles[`badge-${tone}`], pulse && styles.pulse, className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      {...rest}
    />
  );
}

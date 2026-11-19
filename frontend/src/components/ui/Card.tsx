/**
 * Surface primitives: cards, panels and the statistic tiles.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import styles from "./Card.module.css";

/** Props accepted by {@link Card}. */
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Remove the default padding. */
  bare?: boolean;
  /** Add a hover elevation effect. */
  interactive?: boolean;
  /** Render the card as a section with an accessible name. */
  as?: "div" | "section" | "article";
}

/**
 * Render the standard surface container.
 *
 * @param props - The component props.
 * @param ref - The forwarded DOM ref.
 * @returns The card element.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  {
    bare = false,
    interactive = false,
    as = "div",
    className,
    children,
    ...rest
  },
  ref,
) {
  const Tag = as;
  return (
    <Tag
      ref={ref as never}
      className={cn(
        styles.card,
        bare && styles.bare,
        interactive && styles.interactive,
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
});

/** Props accepted by {@link CardHeader}. */
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  /** Actions rendered on the trailing edge of the header. */
  actions?: ReactNode;
}

/**
 * Render the header region of a card.
 *
 * @param props - The component props.
 * @returns The header element.
 */
export function CardHeader({
  actions,
  className,
  children,
  ...rest
}: CardHeaderProps) {
  return (
    <div className={cn(styles.header, className)} {...rest}>
      <div className={styles.headerText}>{children}</div>
      {actions ? <div className={styles.headerActions}>{actions}</div> : null}
    </div>
  );
}

/** Props accepted by {@link CardTitle}. */
export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  /** The heading level, defaults to `h2`. */
  level?: 2 | 3 | 4;
}

/**
 * Render the title of a card.
 *
 * @param props - The component props.
 * @returns The heading element.
 */
export function CardTitle({
  level = 2,
  className,
  children,
  ...rest
}: CardTitleProps) {
  const Tag = `h${level}` as "h2" | "h3" | "h4";
  return (
    <Tag className={cn(styles.title, className)} {...rest}>
      {children}
    </Tag>
  );
}

/**
 * Render the description of a card.
 *
 * @param props - The component props.
 * @returns The description element.
 */
export function CardDescription({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn(styles.description, className)} {...rest}>
      {children}
    </p>
  );
}

/**
 * Render the body region of a card.
 *
 * @param props - The component props.
 * @returns The content element.
 */
export function CardContent({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn(styles.content, className)} {...rest}>
      {children}
    </div>
  );
}

/**
 * Render the footer region of a card.
 *
 * @param props - The component props.
 * @returns The footer element.
 */
export function CardFooter({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn(styles.footer, className)} {...rest}>
      {children}
    </div>
  );
}

/** Props accepted by {@link StatCard}. */
export interface StatCardProps extends HTMLAttributes<HTMLDivElement> {
  /** The label displayed above the value. */
  label: string;
  /** The primary value. */
  value: ReactNode;
  /** Supporting context rendered under the value. */
  meta?: ReactNode;
  /** Icon rendered in the leading corner. */
  icon?: ReactNode;
  /** Accent colour applied to the icon bubble. */
  accent?: string;
  /** Render a loading skeleton instead of the value. */
  loading?: boolean;
  /** Render the change indicator. */
  trend?: { value: string; direction: "up" | "down" | "flat" };
}

/**
 * Render a statistic tile used across the dashboard.
 *
 * @param props - The component props.
 * @returns The tile element.
 */
export function StatCard({
  label,
  value,
  meta,
  icon,
  accent,
  loading = false,
  trend,
  className,
  ...rest
}: StatCardProps) {
  return (
    <div className={cn(styles.stat, className)} {...rest}>
      <div className={styles.statTop}>
        <span className={styles.statLabel}>{label}</span>
        {icon ? (
          <span
            className={styles.statIcon}
            style={
              accent ? { color: accent, background: `${accent}1f` } : undefined
            }
            aria-hidden="true"
          >
            {icon}
          </span>
        ) : null}
      </div>

      {loading ? (
        <div
          className={cn(styles.skeleton, styles.skeletonValue)}
          aria-hidden="true"
        />
      ) : (
        <div className={styles.statValue}>{value}</div>
      )}

      <div className={styles.statMeta}>
        {trend ? (
          <span
            className={cn(styles.trend, styles[`trend-${trend.direction}`])}
          >
            {trend.value}
          </span>
        ) : null}
        {meta ? <span className={styles.meta}>{meta}</span> : null}
      </div>
    </div>
  );
}

/**
 * Render a horizontal section separator.
 *
 * @param props - The component props.
 * @returns The separator element.
 */
export function Divider({
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div role="separator" className={cn(styles.divider, className)} {...rest} />
  );
}

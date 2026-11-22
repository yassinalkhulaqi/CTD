/**
 * SVG score breakdown chart and category contribution list.
 */

import { BarChart3, Droplets, Flame } from "lucide-react";
import { Badge, Card, EmptyState, Skeleton } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { formatScore } from "../scoring";
import type { ScoreBreakdown } from "../types";
import styles from "./ScoreBreakdown.module.css";

/** Props accepted by {@link ScoreBreakdown}. */
export interface ScoreBreakdownProps {
  /** The breakdown to display. */
  breakdown: ScoreBreakdown | null;
  /** Show loading placeholders instead of content. */
  loading?: boolean;
  /** Additional class applied to the container. */
  className?: string;
}

/** Width of the SVG stacked bar viewBox. */
const CHART_WIDTH = 320;
/** Height of the SVG stacked bar viewBox. */
const CHART_HEIGHT = 18;

/**
 * Render the score breakdown chart.
 *
 * @param props - The component props.
 * @returns The breakdown card.
 */
export function ScoreBreakdownChart({
  breakdown,
  loading = false,
  className,
}: ScoreBreakdownProps) {
  if (loading) {
    return (
      <Card as="section" className={cn(styles.card, className)}>
        <Skeleton height={220} />
      </Card>
    );
  }

  if (!breakdown || breakdown.categories.length === 0) {
    return (
      <Card as="section" className={cn(styles.card, className)}>
        <h2 className={styles.title}>Score breakdown</h2>
        <EmptyState
          title="Nothing to break down yet"
          description="Category contributions appear after the first scored solve."
          icon={<BarChart3 size={22} />}
        />
      </Card>
    );
  }

  let offset = 0;
  const segments = breakdown.categories.map((category) => {
    const width = category.share * CHART_WIDTH;
    const segment = { category, x: offset, width };
    offset += width;
    return segment;
  });

  const topSolves = [...breakdown.solves]
    .sort((a, b) => b.points - a.points)
    .slice(0, 4);

  return (
    <Card as="section" className={cn(styles.card, className)}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Score breakdown</h2>
          <p className={styles.subtitle}>
            {breakdown.team_name} · {breakdown.rule.name}
          </p>
        </div>
        <div className={styles.total}>
          <strong>{formatScore(breakdown.total_points)}</strong>
          <span>points</span>
        </div>
      </div>

      <svg
        className={styles.stacked}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Point distribution: ${breakdown.categories
          .map(
            (item) => `${item.label} ${Math.round(item.share * 100)} percent`,
          )
          .join(", ")}`}
      >
        {segments.map(({ category, x, width }) => (
          <rect
            key={category.category}
            x={x}
            y={0}
            width={Math.max(0, width)}
            height={CHART_HEIGHT}
            fill={category.accent}
          >
            <title>{`${category.label}: ${formatScore(category.points)} points`}</title>
          </rect>
        ))}
      </svg>

      <ul className={styles.categories}>
        {breakdown.categories.map((category) => (
          <li key={category.category} className={styles.categoryRow}>
            <span
              className={styles.dot}
              style={{ background: category.accent }}
              aria-hidden="true"
            />
            <div className={styles.categoryBody}>
              <div className={styles.categoryLabel}>
                <span>{category.label}</span>
                <span className={styles.categoryPoints}>
                  {formatScore(category.points)} pts
                </span>
              </div>
              <div className={styles.meter}>
                <span
                  className={styles.meterFill}
                  style={{
                    width: `${Math.max(0, Math.min(100, category.share * 100))}%`,
                    background: category.accent,
                  }}
                />
              </div>
              <span className={styles.categoryMeta}>
                {category.solves} solves · {Math.round(category.share * 100)}%
                of total
              </span>
            </div>
          </li>
        ))}
      </ul>

      <div className={styles.stats}>
        <Badge tone="warning">
          <Flame size={12} /> {breakdown.first_bloods} first bloods
        </Badge>
        <Badge tone="info">
          <Droplets size={12} /> {breakdown.hint_penalties} hint points lost
        </Badge>
      </div>

      {topSolves.length ? (
        <ol className={styles.solves}>
          {topSolves.map((solve) => (
            <li key={solve.solve_id} className={styles.solveRow}>
              <span className={styles.solveTitle}>{solve.title}</span>
              <span className={styles.solveMeta}>
                {solve.category_label} · #{solve.solve_index + 1}
              </span>
              <span className={styles.solvePoints}>
                +{formatScore(solve.points)}
              </span>
            </li>
          ))}
        </ol>
      ) : null}
    </Card>
  );
}

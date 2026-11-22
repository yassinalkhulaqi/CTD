/** Gallery card used to select a chart specification. */

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui";
import type { ChartSpec } from "../types";
import styles from "./ChartCard.module.css";

/** Props accepted by {@link ChartCard}. */
export interface ChartCardProps {
  spec: ChartSpec;
  selected: boolean;
  onSelect: (chartId: string) => void;
}

/** Render a compact preview card for one chart. */
export function ChartCard({ spec, selected, onSelect }: ChartCardProps) {
  return (
    <Card
      as="article"
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      aria-label={`${spec.title} chart`}
    >
      <CardHeader className={styles.header}>
        <CardTitle level={3} className={styles.title}>
          {spec.title}
        </CardTitle>
        <Badge tone={selected ? "accent" : "neutral"} outline={!selected}>
          {spec.chart_type}
        </Badge>
      </CardHeader>
      <CardContent>
        <p className={styles.description}>{spec.team_id} workspace</p>
        <div className={styles.meta}>
          <span>{spec.point_count} points</span>
          <span aria-hidden="true">·</span>
          <span>{spec.palette} palette</span>
        </div>
      </CardContent>
      <CardFooter className={styles.footer}>
        <Button
          size="sm"
          variant={selected ? "primary" : "ghost"}
          aria-pressed={selected}
          onClick={() => onSelect(spec.id)}
        >
          {selected ? "Selected" : "Open chart"}
        </Button>
      </CardFooter>
    </Card>
  );
}

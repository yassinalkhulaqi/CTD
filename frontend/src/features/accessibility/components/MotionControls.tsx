import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Switch,
} from "../../../components/ui";
import type { MotionPreferences } from "../types";
import styles from "./MotionControls.module.css";

export interface MotionControlsProps extends MotionPreferences {
  onReducedMotionChange: (value: boolean) => void;
  onHighContrastChange: (value: boolean) => void;
}

export function MotionControls({
  reducedMotion,
  highContrast,
  onReducedMotionChange,
  onHighContrastChange,
}: MotionControlsProps) {
  return (
    <Card as="section" className={styles.card} aria-labelledby="motion-title">
      <CardHeader
        actions={
          <Badge tone="info" outline>
            Page scoped
          </Badge>
        }
      >
        <CardTitle id="motion-title">Motion and contrast controls</CardTitle>
        <CardDescription>
          These switches affect only the accessibility page, not the global
          theme.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className={styles.switches}>
          <Switch
            checked={reducedMotion}
            onChange={(event) => onReducedMotionChange(event.target.checked)}
            hint="Removes transitions and animation inside this page"
          >
            Reduce motion
          </Switch>
          <Switch
            checked={highContrast}
            onChange={(event) => onHighContrastChange(event.target.checked)}
            hint="Raises border and text contrast inside this page"
          >
            High contrast
          </Switch>
        </div>
        <div
          className={styles.preview}
          data-reduced-motion={reducedMotion}
          data-high-contrast={highContrast}
          aria-label="Motion and contrast preview"
        >
          <span className={styles.pulse} aria-hidden="true" />
          <div>
            <strong>Preview surface</strong>
            <p>Animations and borders respond to the switches above.</p>
          </div>
        </div>
        <p className={styles.note} role="status" aria-live="polite">
          Reduced motion {reducedMotion ? "on" : "off"} · High contrast{" "}
          {highContrast ? "on" : "off"}
        </p>
      </CardContent>
    </Card>
  );
}

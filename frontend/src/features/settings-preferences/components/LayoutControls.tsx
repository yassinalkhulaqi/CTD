import { Select, Switch } from "../../../components/ui";
import { SegmentedControl } from "./SegmentedControl";
import type { LayoutResponse } from "../types";
import styles from "../PreferencesPage.module.css";

interface Props {
  layout: Partial<LayoutResponse>;
  onChange: (patch: Partial<LayoutResponse>) => void;
}

const timezones = [
  "UTC",
  "America/New_York",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Tokyo",
].map((v) => ({ value: v, label: v }));
const dateFormats = [
  "YYYY-MM-DD",
  "DD/MM/YYYY",
  "MM/DD/YYYY",
  "MMM D, YYYY",
].map((v) => ({ value: v, label: v }));

export function LayoutControls({ layout, onChange }: Props) {
  return (
    <div className={styles.layoutGrid}>
      <div className={styles.fieldBlock}>
        <span className={styles.fieldLabel}>Density</span>
        <SegmentedControl
          label="Density"
          value={(layout.density as "compact" | "comfortable") ?? "comfortable"}
          options={[
            { value: "comfortable", label: "Comfortable" },
            { value: "compact", label: "Compact" },
          ]}
          onChange={(value) => onChange({ density: value })}
        />
      </div>
      <div className={styles.fieldBlock}>
        <span className={styles.fieldLabel}>Sidebar position</span>
        <SegmentedControl
          label="Sidebar position"
          value={(layout.sidebar_position as "left" | "right") ?? "left"}
          options={[
            { value: "left", label: "Left" },
            { value: "right", label: "Right" },
          ]}
          onChange={(value) => onChange({ sidebar_position: value })}
        />
      </div>
      <Select
        label="Timezone"
        id="tz-select"
        value={layout.timezone ?? "UTC"}
        options={timezones}
        onChange={(e) => onChange({ timezone: e.target.value })}
      />
      <Select
        label="Date format"
        id="df-select"
        value={layout.date_format ?? "YYYY-MM-DD"}
        options={dateFormats}
        onChange={(e) => onChange({ date_format: e.target.value })}
      />
      <div className={styles.switchRow}>
        <Switch
          label="Show activity panel"
          checked={Boolean(layout.show_activity)}
          onChange={(e) => onChange({ show_activity: e.target.checked })}
        />
      </div>
    </div>
  );
}

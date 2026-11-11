/**
 * The activity feed page.
 */

import { useState } from "react";
import { Activity } from "lucide-react";
import { ActivityFeed } from "../../components/layout/ActivityFeed";
import { useActivityStore } from "../../stores/activityStore";
import type { EventKind } from "../../types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  SegmentedControl,
} from "../../components/ui";
import styles from "./ActivityPage.module.css";

const KIND_OPTIONS = [
  { value: "all" as const, label: "All" },
  { value: "solve.created" as const, label: "Solves" },
  { value: "challenge.created" as const, label: "Challenges" },
  { value: "member.updated" as const, label: "Members" },
  { value: "presence.changed" as const, label: "Presence" },
];

/**
 * Render the activity feed page.
 *
 * @returns The page element.
 */
export default function ActivityPage() {
  const kindFilter = useActivityStore((state) => state.kindFilter);
  const setKindFilter = useActivityStore((state) => state.setKindFilter);
  const [limit, setLimit] = useState(40);

  return (
    <div className={styles.page}>
      <Card>
        <CardHeader
          actions={
            <div className={styles.headerActions}>
              <SegmentedControl
                options={KIND_OPTIONS}
                value={kindFilter}
                onValueChange={(value) => setKindFilter(value as EventKind | "all")}
                label="Event kind"
              />
              <SegmentedControl
                options={[
                  { value: "20", label: "20" },
                  { value: "40", label: "40" },
                  { value: "100", label: "100" },
                ]}
                value={String(limit)}
                onValueChange={(value) => setLimit(Number(value))}
                label="Events shown"
              />
            </div>
          }
        >
          <CardTitle>Activity feed</CardTitle>
        </CardHeader>
        <CardContent>
          <ActivityFeed limit={limit} />
        </CardContent>
      </Card>

      <p className={styles.hint}>
        <Activity size={13} aria-hidden="true" />
        Events arrive in real time through the websocket gateway and are replayed
        from the persisted log after a reconnect.
      </p>
    </div>
  );
}

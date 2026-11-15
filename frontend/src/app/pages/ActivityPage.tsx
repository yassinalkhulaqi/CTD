/**
 * The activity feed page.
 */

import { useState } from "react";
import { Activity } from "lucide-react";
import { ActivityFeed } from "../../components/layout/ActivityFeed";
import { useActivityStore } from "../../stores/activityStore";
import type { EventKind } from "../../types";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
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
  const events = useActivityStore((state) => state.events);
  const paused = useActivityStore((state) => state.paused);
  const [limit, setLimit] = useState(40);

  const total = events.length;
  const solves = events.filter((event) => event.kind === "solve.created").length;

  return (
    <div className={styles.page}>
      <div className={styles.summary}>
        <div className={styles.summaryText}>
          <h2 className={styles.summaryTitle}>Team timeline</h2>
          <p className={styles.summaryMeta}>
            {total} events buffered ? {solves} solves ? {limit} shown
          </p>
        </div>
        <Badge tone={paused ? "warning" : "success"} dot>
          {paused ? "Paused" : "Streaming"}
        </Badge>
      </div>

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
          <CardDescription>
            Newest first. Pause the stream to read without the list shifting.
          </CardDescription>
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

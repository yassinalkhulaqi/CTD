/** Event summary card used in the catalogue grid. */

import { CalendarDays, ExternalLink, Users } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  Progress,
} from "../../../components/ui";
import { cn } from "../../../lib/utils";
import {
  capacityLabel,
  deriveEventStatus,
  FORMAT_LABELS,
  STATUS_LABELS,
  statusTone,
} from "../utils";
import type { CtfEvent, EventStats } from "../types";
import { CountdownRing } from "./CountdownRing";
import styles from "./EventCard.module.css";

/** Props accepted by {@link EventCard}. */
export interface EventCardProps {
  event: CtfEvent;
  now: number;
  stats?: EventStats;
  onRegister: (event: CtfEvent) => void;
  onDetails: (event: CtfEvent) => void;
}

/**
 * Render one event with its status, countdown and registration controls.
 *
 * @param props - The component props.
 * @returns The event card.
 */
export function EventCard({
  event,
  now,
  stats,
  onRegister,
  onDetails,
}: EventCardProps) {
  const status = deriveEventStatus(event, now);
  return (
    <Card as="article" interactive className={cn(styles.card, styles[status])}>
      <span className={styles.accent} aria-hidden="true" />
      <CardHeader
        className={styles.header}
        actions={
          <Badge tone={statusTone(status)} dot pulse={status === "live"}>
            {STATUS_LABELS[status]}
          </Badge>
        }
      >
        <h3 className={styles.name}>{event.name}</h3>
        <p className={styles.format}>{FORMAT_LABELS[event.format]}</p>
      </CardHeader>

      <CardContent className={styles.content}>
        <p className={styles.description}>
          {event.description ||
            "No description has been added for this event yet."}
        </p>
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            <CalendarDays size={14} aria-hidden="true" />
            {new Date(event.starts_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
            })}
          </span>
          <span className={styles.metaItem}>
            <Users size={14} aria-hidden="true" />
            {capacityLabel(event, stats)}
          </span>
        </div>
        {event.tags.length > 0 ? (
          <div className={styles.tags} aria-label="Event tags">
            {event.tags.slice(0, 4).map((tag) => (
              <span key={tag} className={styles.tag}>
                #{tag}
              </span>
            ))}
          </div>
        ) : null}
        <Progress
          value={stats?.fill_percentage ?? 0}
          tone={status === "live" ? "success" : "accent"}
          thin
          label={`${event.name} registration fill`}
          className={styles.progress}
        />
      </CardContent>

      <CardFooter className={styles.footer}>
        <CountdownRing event={event} now={now} size={72} />
        <div className={styles.actions}>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onDetails(event)}
            icon={<ExternalLink size={14} />}
          >
            Details
          </Button>
          <Button
            size="sm"
            onClick={() => onRegister(event)}
            disabled={!event.accepts_registrations}
            title={
              event.accepts_registrations
                ? `Register for ${event.name}`
                : "Registration is closed for this event"
            }
          >
            Register
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

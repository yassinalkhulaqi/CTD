/**
 * A card summarising one event adapter mapping.
 */

import { ArrowRight, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui";
import { eventLabel, eventMapEntries, formatTimestamp } from "../logic";
import type { Adapter } from "../types";
import styles from "./AdapterCard.module.css";

/** Props accepted by {@link AdapterCard}. */
export interface AdapterCardProps {
  adapter: Adapter;
  busy?: boolean;
  onDelete: () => void;
}

/**
 * Render an adapter and its event rewrites.
 *
 * @param props - The card props.
 * @returns The adapter card element.
 */
export function AdapterCard({
  adapter,
  busy = false,
  onDelete,
}: AdapterCardProps) {
  return (
    <Card
      as="article"
      className={styles.card}
      aria-label={`Adapter ${adapter.name}`}
    >
      <CardHeader
        actions={
          <Badge tone="accent" outline>
            {adapter.mapping_count} mappings
          </Badge>
        }
      >
        <CardTitle level={3}>{adapter.name}</CardTitle>
        <CardDescription>
          Created {formatTimestamp(adapter.created_at)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className={styles.mappings}>
          {eventMapEntries(adapter.event_map).map(([source, target]) => (
            <li key={source} className={styles.mapping}>
              <span>{eventLabel(source)}</span>
              <ArrowRight size={13} aria-hidden="true" />
              <code>{eventLabel(target)}</code>
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        <Button
          size="sm"
          variant="danger"
          icon={<Trash2 size={14} />}
          onClick={onDelete}
          disabled={busy}
        >
          Delete adapter
        </Button>
      </CardFooter>
    </Card>
  );
}

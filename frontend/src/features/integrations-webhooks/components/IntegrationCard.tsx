/**
 * A single integration summary with enable, edit and delete actions.
 */

import { Pencil, Send, Trash2, Webhook } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Switch,
} from "../../../components/ui";
import { eventLabel, kindLabel } from "../logic";
import type { Integration } from "../types";
import { SecretField } from "./SecretField";
import styles from "./IntegrationCard.module.css";

/** Props accepted by {@link IntegrationCard}. */
export interface IntegrationCardProps {
  integration: Integration;
  busy?: boolean;
  onToggle: (enabled: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
  onSendTest: () => void;
}

/**
 * Render an integration card.
 *
 * @param props - The card props.
 * @returns The integration card element.
 */
export function IntegrationCard({
  integration,
  busy = false,
  onToggle,
  onEdit,
  onDelete,
  onSendTest,
}: IntegrationCardProps) {
  return (
    <Card
      as="article"
      className={styles.card}
      aria-label={`Integration ${integration.name}`}
    >
      <CardHeader
        actions={
          <Switch
            checked={integration.enabled}
            disabled={busy}
            onChange={(event) => onToggle(event.target.checked)}
            aria-label={`Enable ${integration.name}`}
          >
            {integration.enabled ? "Enabled" : "Paused"}
          </Switch>
        }
      >
        <CardTitle level={3}>{integration.name}</CardTitle>
        <CardDescription>
          <Webhook size={13} aria-hidden="true" /> {integration.endpoint_url}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className={styles.meta}>
          <Badge tone="accent" outline>
            {kindLabel(integration.kind)}
          </Badge>
          <Badge tone={integration.enabled ? "success" : "neutral"} dot>
            {integration.is_active ? "Receiving events" : "Inactive"}
          </Badge>
          <Badge tone="neutral">{integration.host}</Badge>
        </div>
        <div className={styles.events} aria-label="Subscribed events">
          {integration.events.map((event) => (
            <Badge key={event} tone="info" outline>
              {eventLabel(event)}
            </Badge>
          ))}
          {integration.events.length === 0 ? (
            <span className={styles.empty}>No events subscribed</span>
          ) : null}
        </div>
        <SecretField
          label="Signing secret"
          value={integration.masked_secret}
          disabled
          configured={integration.has_secret}
          hint={
            integration.has_secret
              ? "Saved digest"
              : "Add a secret to sign payloads"
          }
        />
      </CardContent>
      <CardFooter>
        <Button
          size="sm"
          variant="secondary"
          icon={<Pencil size={14} />}
          onClick={onEdit}
          disabled={busy}
        >
          Edit
        </Button>
        <Button
          size="sm"
          variant="secondary"
          icon={<Send size={14} />}
          onClick={onSendTest}
          disabled={busy || !integration.enabled}
        >
          Send test
        </Button>
        <Button
          size="sm"
          variant="danger"
          icon={<Trash2 size={14} />}
          onClick={onDelete}
          disabled={busy}
        >
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}

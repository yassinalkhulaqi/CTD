/**
 * Inspection panel for the delivery ledger.
 */

import { useState } from "react";
import { ChevronDown, RotateCcw, ShieldCheck } from "lucide-react";
import { Badge, Button, EmptyState } from "../../../components/ui";
import {
  deliveryTone,
  eventLabel,
  formatTimestamp,
  retryLabel,
} from "../logic";
import type { Delivery, DeliveryStatus, Integration } from "../types";
import styles from "./DeliveryInspector.module.css";

/** Props accepted by {@link DeliveryInspector}. */
export interface DeliveryInspectorProps {
  deliveries: Delivery[];
  integrations: Integration[];
  busyId?: string | null;
  onRetry: (id: string) => void;
  onSimulate?: (id: string, status: DeliveryStatus) => void;
}

/**
 * Render the delivery ledger with a payload inspector and retry controls.
 *
 * @param props - The inspector props.
 * @returns The delivery inspector element.
 */
export function DeliveryInspector({
  deliveries,
  integrations,
  busyId = null,
  onRetry,
  onSimulate,
}: DeliveryInspectorProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const names = new Map(integrations.map((item) => [item.id, item.name]));

  if (deliveries.length === 0) {
    return (
      <EmptyState
        title="No deliveries yet"
        description="Dispatch an event to see signed payloads and transport attempts here."
      />
    );
  }

  return (
    <div className={styles.list} role="list" aria-label="Delivery ledger">
      {deliveries.map((delivery) => {
        const isOpen = expanded === delivery.id;
        return (
          <div
            key={delivery.id}
            role="listitem"
            className={isOpen ? `${styles.row} ${styles.rowOpen}` : styles.row}
          >
            <div className={styles.summary}>
              <button
                type="button"
                className={styles.toggle}
                aria-expanded={isOpen}
                aria-controls={`payload-${delivery.id}`}
                onClick={() => setExpanded(isOpen ? null : delivery.id)}
              >
                <ChevronDown
                  size={15}
                  className={isOpen ? styles.chevronOpen : styles.chevron}
                  aria-hidden="true"
                />
                <span className={styles.event}>
                  {eventLabel(delivery.event)}
                </span>
              </button>
              <Badge tone={deliveryTone(delivery.status)} dot>
                {delivery.status_label}
              </Badge>
              <span className={styles.target}>
                {names.get(delivery.integration_id) ?? delivery.integration_id}
              </span>
              <span className={styles.metric}>
                {delivery.attempts} attempts
              </span>
              <span className={styles.metric}>
                {delivery.response_code === null
                  ? "no response"
                  : `HTTP ${delivery.response_code}`}
              </span>
              <span className={styles.metric}>
                {formatTimestamp(delivery.sent_at)}
              </span>
              <Button
                size="sm"
                variant="secondary"
                icon={<RotateCcw size={13} />}
                disabled={!delivery.can_retry || busyId === delivery.id}
                aria-label={`Retry delivery ${delivery.id}`}
                onClick={() => onRetry(delivery.id)}
              >
                Retry
              </Button>
            </div>
            {onSimulate && delivery.can_retry ? (
              <div className={styles.simulate}>
                <span>Simulate result</span>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busyId === delivery.id}
                  onClick={() => onSimulate(delivery.id, "success")}
                >
                  Success
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busyId === delivery.id}
                  onClick={() => onSimulate(delivery.id, "failed")}
                >
                  Failure
                </Button>
              </div>
            ) : null}
            {isOpen ? (
              <div id={`payload-${delivery.id}`} className={styles.payload}>
                <pre>{JSON.stringify(delivery.payload, null, 2)}</pre>
                <div className={styles.signature}>
                  {delivery.signature ? (
                    <>
                      <ShieldCheck size={14} aria-hidden="true" />
                      <code>{delivery.signature}</code>
                    </>
                  ) : (
                    <span>Unsigned delivery</span>
                  )}
                  <span className={styles.backoff}>
                    Next backoff {retryLabel(delivery.retry_after_seconds)}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Domain types and constants for the integrations screen.
 */

export type IntegrationKind = "webhook" | "slack" | "ctf_platform";
export type DeliveryStatus = "pending" | "success" | "failed";
export type BadgeTone =
  "neutral" | "accent" | "success" | "warning" | "danger" | "info";

export interface Integration {
  id: string;
  name: string;
  kind: IntegrationKind;
  endpoint_url: string;
  events: string[];
  masked_secret: string;
  has_secret: boolean;
  enabled: boolean;
  created_at: string;
  host: string;
  scheme: string;
  event_count: number;
  is_active: boolean;
  subscribers_label: string;
}

export interface Delivery {
  id: string;
  integration_id: string;
  event: string;
  payload: Record<string, unknown>;
  status: DeliveryStatus;
  attempts: number;
  response_code: number | null;
  sent_at: string | null;
  signature: string;
  can_retry: boolean;
  retry_after_seconds: number;
  status_label: string;
}

export interface Adapter {
  id: string;
  name: string;
  event_map: Record<string, string>;
  mapping_count: number;
  created_at: string;
}

export interface IntegrationStats {
  total_integrations: number;
  enabled_integrations: number;
  total_adapters: number;
  total_deliveries: number;
  pending_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  success_rate: number;
  failure_rate: number;
  average_attempts: number;
  last_sent_at: string | null;
  by_event: Record<string, number>;
  by_kind: Record<string, number>;
}

export interface IntegrationDraft {
  name: string;
  kind: IntegrationKind;
  endpoint_url: string;
  events: string[];
  secret: string;
  enabled: boolean;
}

export interface IntegrationCreateInput {
  name: string;
  kind: IntegrationKind;
  endpoint_url: string;
  events: string[];
  secret: string;
  enabled: boolean;
}

export interface IntegrationUpdateInput {
  name?: string;
  kind?: IntegrationKind;
  endpoint_url?: string;
  events?: string[];
  secret?: string;
  enabled?: boolean;
}

export interface AdapterCreateInput {
  name: string;
  event_map: Record<string, string>;
}

export interface DispatchInput {
  event: string;
  payload: Record<string, unknown>;
  simulate_status?: DeliveryStatus | null;
  response_code?: number | null;
}

export interface SimulationInput {
  status: DeliveryStatus;
  response_code: number | null;
}

/** The transport choices offered by the integration form. */
export const INTEGRATION_KINDS: ReadonlyArray<{
  value: IntegrationKind;
  label: string;
  hint: string;
}> = [
  { value: "webhook", label: "Webhook", hint: "Signed HTTPS callback" },
  { value: "slack", label: "Slack", hint: "Incoming webhook message" },
  {
    value: "ctf_platform",
    label: "CTF platform",
    hint: "Competition API bridge",
  },
];

/** The statuses rendered by the delivery inspector. */
export const DELIVERY_STATUSES: ReadonlyArray<{
  value: DeliveryStatus;
  label: string;
}> = [
  { value: "pending", label: "Pending" },
  { value: "success", label: "Delivered" },
  { value: "failed", label: "Failed" },
];

/** Events an integration may subscribe to, mirroring the backend allowlist. */
export const ALL_EVENTS: readonly string[] = [
  "challenge.created",
  "challenge.solved",
  "event.started",
  "event.ended",
  "flag.submitted",
  "hint.revealed",
  "member.joined",
  "score.changed",
  "solve.created",
  "submission.failed",
  "team.updated",
  "writeup.published",
];

/** Human readable labels for the allowlisted events. */
export const EVENT_LABELS: Readonly<Record<string, string>> = {
  "challenge.created": "Challenge created",
  "challenge.solved": "Challenge solved",
  "event.started": "Event started",
  "event.ended": "Event ended",
  "flag.submitted": "Flag submitted",
  "hint.revealed": "Hint revealed",
  "member.joined": "Member joined",
  "score.changed": "Score changed",
  "solve.created": "Solve created",
  "submission.failed": "Submission failed",
  "team.updated": "Team updated",
  "writeup.published": "Writeup published",
};

/** Labels for the transport kinds. */
export const KIND_LABELS: Readonly<Record<IntegrationKind, string>> = {
  webhook: "Webhook",
  slack: "Slack",
  ctf_platform: "CTF platform",
};

/** A blank draft used by the create form. */
export const EMPTY_DRAFT: IntegrationDraft = {
  name: "",
  kind: "webhook",
  endpoint_url: "",
  events: ["challenge.solved"],
  secret: "",
  enabled: true,
};

/**
 * Domain types for the offline mutation queue and reconciliation screen.
 */

/** The kind of local change captured by a mutation. */
export type MutationOperation = "create" | "update" | "delete";

/** Lifecycle of a mutation inside the queue. */
export type MutationStatus = "pending" | "synced" | "conflict";

/** Strategy used to settle a version conflict. */
export type ConflictStrategy = "local_wins" | "remote_wins" | "merge";

/** Outcome of pushing one mutation during a batch. */
export type SyncOutcome = "applied" | "conflict" | "skipped" | "failed";

/** Coarse queue health label returned by the status endpoint. */
export type SyncHealth = "idle" | "syncing" | "attention" | "healthy";

/** Visual tone shared with the design system badges. */
export type StatusTone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info";

/** Browser connectivity state rendered by the banner. */
export type Connectivity = "online" | "offline";

/** A JSON object payload carried by a mutation. */
export type Payload = Record<string, unknown>;

/** A mutation queued on the server while the client was offline. */
export interface PendingMutation {
  id: string;
  client_id: string;
  entity: string;
  operation: MutationOperation;
  payload: Payload;
  base_version: number;
  created_at: string;
  status: MutationStatus;
  attempts: number;
  last_error: string;
  resolved_version: number | null;
  entity_label: string;
  is_pending: boolean;
  next_retry_delay: number;
}

/** A completed synchronisation batch. */
export interface SyncSnapshot {
  id: string;
  client_id: string;
  synced_at: string;
  version: number;
  mutation_count: number;
  conflict_count: number;
  note: string;
  total_count: number;
  success_rate: number;
}

/** Response returned by the queue endpoint. */
export interface QueueResponse {
  client_id: string | null;
  items: PendingMutation[];
  total: number;
  pending: number;
  conflicts: number;
  oldest_first: boolean;
}

/** Request body used to enqueue a mutation. */
export interface MutationCreate {
  client_id: string;
  entity: string;
  operation: MutationOperation;
  payload: Payload;
  base_version?: number;
  mutation_id?: string;
}

/** Request body controlling a processing batch. */
export interface ProcessRequest {
  client_id?: string;
  limit?: number;
  current_versions?: Record<string, number>;
}

/** One outcome from a processing batch. */
export interface MutationOutcome {
  mutation_id: string;
  entity: string;
  operation: MutationOperation;
  result: SyncOutcome;
  detail: string;
  succeeded: boolean;
  needs_attention: boolean;
}

/** Response returned by the process endpoint. */
export interface ProcessResponse {
  outcomes: MutationOutcome[];
  processed: number;
  applied: number;
  conflicts: number;
  skipped: number;
  failed: number;
  success_rate: number;
  started_at: string;
  finished_at: string;
  snapshot: SyncSnapshot | null;
}

/** One field decision captured on a conflict resolution. */
export interface FieldChange {
  field: string;
  local_value: unknown;
  remote_value: unknown;
  chosen_value: unknown;
  contested: boolean;
  chose_local: boolean;
  summary: string;
}

/** Request body used to resolve a conflict. */
export interface ConflictResolveRequest {
  strategy: ConflictStrategy;
  note?: string;
  remote_payload?: Payload;
  base_payload?: Payload;
}

/** A persisted conflict decision. */
export interface ConflictResolution {
  id: string;
  mutation_id: string;
  strategy: ConflictStrategy;
  resolved_at: string;
  local_version: number;
  remote_version: number;
  notes: string;
  strategy_label: string;
  version_gap: number;
  was_merged: boolean;
  summary: string;
  field_changes: FieldChange[];
}

/** Queue health summary shown by the status card. */
export interface SyncStatus {
  pending: number;
  synced: number;
  conflict: number;
  total: number;
  attempts: number;
  backlog: number;
  completion_rate: number;
  average_attempts: number;
  health_label: SyncHealth;
  has_conflicts: boolean;
  oldest_pending: string | null;
  newest_synced: string | null;
  stale: boolean;
  resolution_count: number;
  latest_snapshot: SyncSnapshot | null;
}

/** Response returned after clearing synchronised entries. */
export interface ClearResponse {
  client_id: string | null;
  deleted: number;
  remaining: number;
}

/** Optional filters accepted by the queue endpoint. */
export interface QueueFilters {
  clientId?: string;
  status?: MutationStatus;
  entity?: string;
  limit?: number;
}

/** Result of previewing a three-way merge in the dialog. */
export interface MergePreview {
  payload: Payload;
  contested: string[];
  fields: string[];
}

/** Description of a connectivity state used by the banner. */
export interface ConnectivityCopy {
  title: string;
  detail: string;
  tone: StatusTone;
}

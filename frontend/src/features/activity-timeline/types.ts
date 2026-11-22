/**
 * Domain types and view models for the activity timeline feature.
 */

/** The categories of activity recorded by the timeline. */
export type TimelineKind =
  | "solve"
  | "challenge"
  | "member"
  | "team"
  | "note"
  | "hint"
  | "submission"
  | "achievement"
  | "system";

/** The importance tiers attached to events. */
export type Importance = "low" | "normal" | "high" | "critical";

/** The temporal granularity of a timeline bucket. */
export type BucketLevel = "day" | "hour";

/** A single activity record returned by the API. */
export interface TimelineEvent {
  id: string;
  team_id: string;
  kind: string;
  actor_id: string;
  actor_name: string;
  summary: string;
  payload_json: string;
  importance: Importance;
  occurred_at: string;
  kind_label: string;
  kind_icon: string;
  kind_color: string;
  importance_label: string;
  importance_tone: string;
  importance_rank: number;
  actor_initials: string;
  date_key: string;
  hour_key: string;
  hour_of_day: number;
  relative_label: string;
}

/** One or more consecutive events collapsed into a single display item. */
export interface EventCluster {
  id: string;
  event: TimelineEvent;
  count: number;
  first_at: string;
  last_at: string;
  is_merged: boolean;
  count_label: string;
  importance_rank: number;
}

/** A day or hour bucket of clustered events. */
export interface TimelineBucket {
  key: string;
  label: string;
  level: BucketLevel;
  events: EventCluster[];
  children: TimelineBucket[];
  count: number;
  item_count: number;
  critical_count: number;
  peak_importance: Importance;
}

/** A paginated timeline page. */
export interface TimelinePage {
  events: TimelineEvent[];
  clusters: EventCluster[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset: number | null;
  page_number: number;
}

/** Aggregated timeline counters. */
export interface TimelineStats {
  total: number;
  by_kind: Record<string, number>;
  by_hour: Record<string, number>;
  by_importance: Record<string, number>;
  unique_actors: number;
  critical_count: number;
  first_seen: string | null;
  last_seen: string | null;
  generated_at: string;
  busiest_kind: string | null;
  busiest_hour: string | null;
  critical_ratio: number;
  average_per_hour: number;
  top_kinds: Array<[string, number]>;
}

/** Aggregated activity for one actor. */
export interface ActorSummary {
  actor_id: string;
  actor_name: string;
  event_count: number;
  critical_count: number;
  last_seen: string | null;
  kinds: string[];
  label: string;
  initials: string;
  first_kind: string;
}

/** The outcome of an age based prune. */
export interface PruneResult {
  cutoff: string;
  deleted: number;
  max_age_days: number;
  retained: number;
  description: string;
}

/** A kind option presented by the filter chips. */
export interface KindOption {
  value: TimelineKind;
  label: string;
  color: string;
}

/** Query parameters accepted by the timeline endpoints. */
export interface TimelineQuery {
  kinds?: string[];
  actors?: string[];
  importance?: Importance[];
  teamId?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

/** The payload accepted when an event is recorded. */
export interface TimelineCreatePayload {
  team_id: string;
  kind: string;
  actor_id: string;
  actor_name: string;
  summary: string;
  payload?: Record<string, unknown>;
  importance?: Importance;
  occurred_at?: string;
}

/** A flattened row of the virtual-style timeline list. */
export type TimelineRow =
  | { type: "day"; key: string; bucket: TimelineBucket }
  | { type: "hour"; key: string; bucket: TimelineBucket }
  | { type: "event"; key: string; cluster: EventCluster };

/** The state of the live "new events" banner. */
export interface LiveState {
  pending: number;
  lastSeenId: string | null;
}

/**
 * Typed API adapter for the activity timeline feature.
 *
 * Every request goes through the shared HTTP client so authentication, retries
 * and error normalisation behave exactly like the rest of the application.
 */

import {
  buildQuery,
  del,
  get,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  ActorSummary,
  PruneResult,
  TimelineBucket,
  TimelineCreatePayload,
  TimelineEvent,
  TimelinePage,
  TimelineQuery,
  TimelineStats,
} from "./types";

/**
 * Encode an identifier for use in a URL path.
 *
 * @param id - The raw identifier.
 * @returns The percent encoded identifier.
 */
function pathId(id: string): string {
  return encodeURIComponent(id);
}

/**
 * Build a query string for a timeline request.
 *
 * Repeated parameters are appended explicitly because the shared helper
 * accepts scalar values only.
 *
 * @param filters - The filters to encode.
 * @returns The query string, including its leading `?` when needed.
 */
export function buildTimelineQuery(filters: TimelineQuery = {}): string {
  const scalar = buildQuery({
    team_id: filters.teamId,
    from: filters.from,
    to: filters.to,
    limit: filters.limit,
    offset: filters.offset,
  });
  const params = new URLSearchParams(
    scalar.startsWith("?") ? scalar.slice(1) : scalar,
  );
  for (const kind of filters.kinds ?? []) params.append("kinds", kind);
  for (const actor of filters.actors ?? []) params.append("actors", actor);
  for (const tier of filters.importance ?? [])
    params.append("importance", tier);
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

/** The activity timeline endpoints. */
export const timelineApi = {
  /**
   * List events with filters and pagination.
   *
   * @param filters - Optional filters.
   * @param options - Request options.
   * @returns The event page.
   */
  listEvents(
    filters: TimelineQuery = {},
    options?: RequestOptions,
  ): Promise<TimelinePage> {
    return get<TimelinePage>(
      `/api/timeline${buildTimelineQuery(filters)}`,
      options,
    );
  },

  /**
   * Record a new activity event.
   *
   * @param payload - The event fields.
   * @param options - Request options.
   * @returns The created event.
   */
  createEvent(
    payload: TimelineCreatePayload,
    options?: RequestOptions,
  ): Promise<TimelineEvent> {
    return post<TimelineEvent>("/api/timeline", payload, options);
  },

  /**
   * Return events grouped by day and hour.
   *
   * @param filters - Optional filters.
   * @param options - Request options.
   * @returns The bucket hierarchy.
   */
  getGroups(
    filters: TimelineQuery = {},
    options?: RequestOptions,
  ): Promise<TimelineBucket[]> {
    return get<TimelineBucket[]>(
      `/api/timeline/groups${buildTimelineQuery(filters)}`,
      options,
    );
  },

  /**
   * Return aggregated timeline statistics.
   *
   * @param filters - Optional filters.
   * @param options - Request options.
   * @returns The aggregated counters.
   */
  getStats(
    filters: TimelineQuery = {},
    options?: RequestOptions,
  ): Promise<TimelineStats> {
    return get<TimelineStats>(
      `/api/timeline/stats${buildTimelineQuery(filters)}`,
      options,
    );
  },

  /**
   * Return actors ordered by activity.
   *
   * @param teamId - Optional team restriction.
   * @param options - Request options.
   * @returns The actor summaries.
   */
  getActors(
    teamId?: string,
    options?: RequestOptions,
  ): Promise<ActorSummary[]> {
    return get<ActorSummary[]>(
      `/api/timeline/actors${buildQuery({ team_id: teamId })}`,
      options,
    );
  },

  /**
   * Return the kinds currently present in the timeline.
   *
   * @param options - Request options.
   * @returns The kind values.
   */
  getKinds(
    options?: RequestOptions,
  ): Promise<{ kinds: string[]; count: number }> {
    return get<{ kinds: string[]; count: number }>(
      "/api/timeline/kinds",
      options,
    );
  },

  /**
   * Delete a single event.
   *
   * @param id - The event identifier.
   * @param options - Request options.
   * @returns A confirmation payload.
   */
  deleteEvent(
    id: string,
    options?: RequestOptions,
  ): Promise<{ id: string; deleted: boolean }> {
    return del<{ id: string; deleted: boolean }>(
      `/api/timeline/${pathId(id)}`,
      options,
    );
  },

  /**
   * Delete events older than the requested age.
   *
   * @param maxAgeDays - Maximum age in days.
   * @param options - Request options.
   * @returns The prune result.
   */
  prune(maxAgeDays: number, options?: RequestOptions): Promise<PruneResult> {
    const query = buildQuery({ max_age_days: maxAgeDays });
    return post<PruneResult>(`/api/timeline/prune${query}`, undefined, options);
  },
};

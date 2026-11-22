/** Typed HTTP adapter for the event lifecycle API. */

import { buildQuery, del, get, patch, post } from "../../api/client";
import type {
  CancellationResult,
  CtfEvent,
  EventCreatePayload,
  EventList,
  EventOverlap,
  EventQuery,
  EventStats,
  EventTask,
  EventUpdatePayload,
  RegistrationLedger,
  EventRegistration,
  TeamOption,
} from "./types";

/** Options shared by every adapter call. */
export interface CallOptions {
  signal?: AbortSignal;
}

/** The event feature endpoints. */
export const eventsApi = {
  /**
   * Return a filtered catalogue of events.
   *
   * @param query - Optional filters.
   * @param options - Request options.
   * @returns The event list.
   */
  list(query: EventQuery = {}, options: CallOptions = {}): Promise<EventList> {
    return get<EventList>(`/api/events${buildQuery({ ...query })}`, options);
  },

  /**
   * Return upcoming events.
   *
   * @param options - Request options.
   * @returns The event list.
   */
  upcoming(options: CallOptions = {}): Promise<EventList> {
    return get<EventList>("/api/events/upcoming", options);
  },

  /**
   * Return live events.
   *
   * @param options - Request options.
   * @returns The event list.
   */
  live(options: CallOptions = {}): Promise<EventList> {
    return get<EventList>("/api/events/live", options);
  },

  /**
   * Return one event.
   *
   * @param eventId - The event identifier.
   * @param options - Request options.
   * @returns The event.
   */
  get(eventId: string, options: CallOptions = {}): Promise<CtfEvent> {
    return get<CtfEvent>(`/api/events/${encodeURIComponent(eventId)}`, options);
  },

  /**
   * Create an event.
   *
   * @param payload - The event fields.
   * @param options - Request options.
   * @returns The created event.
   */
  create(
    payload: EventCreatePayload,
    options: CallOptions = {},
  ): Promise<CtfEvent> {
    return post<CtfEvent>("/api/events", payload, options);
  },

  /**
   * Edit an event.
   *
   * @param eventId - The event identifier.
   * @param payload - The fields to change.
   * @param options - Request options.
   * @returns The updated event.
   */
  update(
    eventId: string,
    payload: EventUpdatePayload,
    options: CallOptions = {},
  ): Promise<CtfEvent> {
    return patch<CtfEvent>(
      `/api/events/${encodeURIComponent(eventId)}`,
      payload,
      options,
    );
  },

  /**
   * Delete an event.
   *
   * @param eventId - The event identifier.
   * @param options - Request options.
   */
  remove(eventId: string, options: CallOptions = {}): Promise<void> {
    return del<void>(`/api/events/${encodeURIComponent(eventId)}`, options);
  },

  /**
   * Register a team for an event.
   *
   * @param eventId - The event identifier.
   * @param teamId - The team identifier.
   * @param options - Request options.
   * @returns The new registration.
   */
  register(
    eventId: string,
    teamId: string,
    options: CallOptions = {},
  ): Promise<EventRegistration> {
    return post<EventRegistration>(
      `/api/events/${encodeURIComponent(eventId)}/register`,
      { team_id: teamId },
      options,
    );
  },

  /**
   * Cancel a team's registration.
   *
   * @param eventId - The event identifier.
   * @param teamId - The team identifier.
   * @param options - Request options.
   * @returns The cancellation outcome.
   */
  cancel(
    eventId: string,
    teamId: string,
    options: CallOptions = {},
  ): Promise<CancellationResult> {
    return post<CancellationResult>(
      `/api/events/${encodeURIComponent(eventId)}/cancel`,
      { team_id: teamId },
      options,
    );
  },

  /**
   * Return the registration ledger of an event.
   *
   * @param eventId - The event identifier.
   * @param options - Request options.
   * @returns The ledger.
   */
  registrations(
    eventId: string,
    options: CallOptions = {},
  ): Promise<RegistrationLedger> {
    return get<RegistrationLedger>(
      `/api/events/${encodeURIComponent(eventId)}/registrations`,
      options,
    );
  },

  /**
   * Return registration statistics of an event.
   *
   * @param eventId - The event identifier.
   * @param options - Request options.
   * @returns The statistics.
   */
  stats(eventId: string, options: CallOptions = {}): Promise<EventStats> {
    return get<EventStats>(
      `/api/events/${encodeURIComponent(eventId)}/stats`,
      options,
    );
  },

  /**
   * Return statistics for every event.
   *
   * @param options - Request options.
   * @returns The statistics keyed by event identifier.
   */
  allStats(options: CallOptions = {}): Promise<{ events: EventStats[] }> {
    return get<{ events: EventStats[] }>("/api/events/stats", options);
  },

  /**
   * Return the checklist of an event.
   *
   * @param eventId - The event identifier.
   * @param options - Request options.
   * @returns The checklist items.
   */
  tasks(eventId: string, options: CallOptions = {}): Promise<EventTask[]> {
    return get<EventTask[]>(
      `/api/events/${encodeURIComponent(eventId)}/tasks`,
      options,
    );
  },

  /**
   * Add a checklist item.
   *
   * @param eventId - The event identifier.
   * @param title - The item title.
   * @param dueAt - Optional ISO due date.
   * @param options - Request options.
   * @returns The created item.
   */
  addTask(
    eventId: string,
    title: string,
    dueAt?: string,
    options: CallOptions = {},
  ): Promise<EventTask> {
    return post<EventTask>(
      `/api/events/${encodeURIComponent(eventId)}/tasks`,
      { title, due_at: dueAt ?? null },
      options,
    );
  },

  /**
   * Toggle a checklist item.
   *
   * @param eventId - The event identifier.
   * @param taskId - The checklist item identifier.
   * @param options - Request options.
   * @returns The updated item.
   */
  toggleTask(
    eventId: string,
    taskId: string,
    options: CallOptions = {},
  ): Promise<EventTask> {
    return post<EventTask>(
      `/api/events/${encodeURIComponent(eventId)}/tasks/${encodeURIComponent(taskId)}/toggle`,
      undefined,
      options,
    );
  },

  /**
   * Return the teams that can be selected during registration.
   *
   * @param options - Request options.
   * @returns The teams.
   */
  teams(options: CallOptions = {}): Promise<TeamOption[]> {
    return get<TeamOption[]>("/api/teams", options);
  },

  /**
   * Return live event clashes for a team.
   *
   * @param teamId - The team identifier.
   * @param options - Request options.
   * @returns The conflicts.
   */
  overlaps(
    teamId: string,
    options: CallOptions = {},
  ): Promise<{
    team_id: string;
    overlaps: EventOverlap[];
  }> {
    return get<{ team_id: string; overlaps: EventOverlap[] }>(
      `/api/events/overlaps${buildQuery({ team_id: teamId })}`,
      options,
    );
  },
};

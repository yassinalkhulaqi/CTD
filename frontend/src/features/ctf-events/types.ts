/** Domain types of the event lifecycle feature. */

/** Lifecycle state of an event as computed by the API. */
export type EventStatus = "draft" | "upcoming" | "live" | "archived";

/** Scoring format of an event. */
export type EventFormat = "jeopardy" | "attack_defence";

/** State of a team's registration. */
export type RegistrationStatus = "confirmed" | "waitlisted" | "cancelled";

/** Catalogue window accepted by the event filters. */
export type EventWindow = "all" | "draft" | "upcoming" | "live" | "archived";

/** A CTF event returned by the API. */
export interface CtfEvent {
  id: string;
  name: string;
  slug: string;
  description: string;
  format: EventFormat;
  starts_at: string;
  ends_at: string;
  status: EventStatus;
  stored_status: EventStatus;
  max_team_size: number;
  registration_open: boolean;
  website_url: string;
  tags: string[];
  created_at: string;
  countdown_seconds: number;
  countdown_label: string;
  seconds_until_start: number;
  seconds_remaining: number;
  duration_seconds: number;
  progress: number;
  is_live: boolean;
  is_upcoming: boolean;
  is_archived: boolean;
  accepts_registrations: boolean;
}

/** A team's place in an event's registration ledger. */
export interface EventRegistration {
  id: string;
  event_id: string;
  team_id: string;
  status: RegistrationStatus;
  registered_at: string;
  is_confirmed: boolean;
  is_waitlisted: boolean;
}

/** A checklist item attached to an event. */
export interface EventTask {
  id: string;
  event_id: string;
  title: string;
  done: boolean;
  due_at: string | null;
  is_overdue: boolean;
}

/** Aggregated registration figures of an event. */
export interface EventStats {
  event_id: string;
  capacity: number;
  confirmed: number;
  waitlisted: number;
  cancelled: number;
  promotions: number;
  total: number;
  available_slots: number;
  is_full: boolean;
  capacity_ratio: number;
  fill_percentage: number;
  waitlist_pressure: number;
}

/** A filtered list of events. */
export interface EventList {
  events: CtfEvent[];
  total: number;
  window: EventWindow;
}

/** The registration ledger of an event. */
export interface RegistrationLedger {
  event_id: string;
  registrations: EventRegistration[];
  confirmed: number;
  waitlisted: number;
}

/** Outcome of a cancellation. */
export interface CancellationResult {
  event_id: string;
  team_id: string;
  status: RegistrationStatus;
  promoted_team_id: string | null;
  promotion: EventRegistration | null;
}

/** A team available in the registration selector. */
export interface TeamOption {
  id: string;
  name: string;
  slug: string;
  color: string;
}

/** Payload used to create an event. */
export interface EventCreatePayload {
  name: string;
  starts_at: string;
  ends_at: string;
  description?: string;
  format?: EventFormat;
  status?: EventStatus;
  max_team_size?: number;
  registration_open?: boolean;
  website_url?: string;
  tags?: string[];
}

/** Payload used to edit an event. */
export type EventUpdatePayload = Partial<EventCreatePayload>;

/** Query parameters accepted by the event catalogue. */
export interface EventQuery {
  status?: EventStatus;
  format?: EventFormat;
  tag?: string;
  search?: string;
  registration_open?: boolean;
  window?: EventWindow;
  limit?: number;
}

/** A scheduling conflict reported by the overlap endpoint. */
export interface EventOverlap {
  team_id: string;
  first_event_id: string;
  first_event_name: string;
  second_event_id: string;
  second_event_name: string;
  overlap_seconds: number;
}

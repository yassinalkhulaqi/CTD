/**
 * Types of the team roster feature.
 *
 * The shapes mirror the JSON returned by the `/api/roster` endpoints so the
 * UI can render derived values without recomputing domain rules locally.
 */

/** Roles recognised by the roster domain, ordered from junior to senior. */
export type RosterRole = "observer" | "analyst" | "member" | "lead";

/** Availability states a member can advertise. */
export type Availability = "available" | "busy" | "offline";

/** Lifecycle states of an invitation. */
export type InvitationStatus = "pending" | "accepted" | "expired" | "revoked";

/** Capabilities granted by roster roles. */
export type RosterPermission =
  | "roster:view"
  | "roster:contacts"
  | "roster:work"
  | "roster:assign"
  | "roster:invite"
  | "roster:roles"
  | "roster:manage";

/** Semantic colour tone used by the shared design system. */
export type RosterTone =
  "neutral" | "accent" | "success" | "warning" | "danger" | "info";

/** A member of a team roster. */
export interface RosterMember {
  id: string;
  team_id: string;
  handle: string;
  display_name: string;
  role: RosterRole;
  specialty: string;
  timezone: string;
  availability: Availability;
  capacity_hours: number;
  joined_at: string;
  initials: string;
  rank: number;
  availability_label: string;
  accepts_work: boolean;
}

/** An invitation to join a team. */
export interface Invitation {
  id: string;
  team_id: string;
  email: string;
  role: RosterRole;
  token: string;
  status: InvitationStatus;
  created_at: string;
  expires_at: string;
  masked_token: string;
  effective_status: InvitationStatus;
}

/** A block of work reserved for a member. */
export interface RosterAssignment {
  id: string;
  member_id: string;
  challenge_id: string;
  hours: number;
  assigned_at: string;
}

/** Aggregated roster statistics grouped by role and availability. */
export interface RosterStats {
  team_id: string | null;
  total_members: number;
  total_capacity_hours: number;
  assigned_hours: number;
  assignment_count: number;
  pending_invitations: number;
  by_role: Record<string, number>;
  by_availability: Record<string, number>;
  utilisation: number;
  utilisation_percent: number;
  remaining_hours: number;
  available_count: number;
  lead_count: number;
}

/** Result of accepting an invitation. */
export interface AcceptanceResult {
  member: RosterMember;
  invitation: Invitation;
}

/** Payload accepted by the member creation endpoint. */
export interface RosterMemberInput {
  team_id: string;
  handle: string;
  display_name?: string;
  role?: RosterRole;
  specialty?: string;
  timezone?: string;
  availability?: Availability;
  capacity_hours?: number;
}

/** Payload accepted by the member update endpoints. */
export interface RosterMemberPatch {
  handle?: string;
  display_name?: string;
  specialty?: string;
  timezone?: string;
  availability?: Availability;
  capacity_hours?: number;
}

/** Payload accepted by the invitation endpoint. */
export interface InvitationInput {
  team_id: string;
  email: string;
  role?: RosterRole;
}

/** Payload accepted by the assignment endpoint. */
export interface AssignmentInput {
  member_id: string;
  challenge_id: string;
  hours: number;
}

/** Filters applied to the roster table. */
export interface MemberFilters {
  teamId: string;
  role: RosterRole | "all";
  availability: Availability | "all";
  query: string;
}

/** Available sort keys for the roster table. */
export type MemberSortKey = "name" | "role" | "availability" | "capacity";

/** Layout used to present the roster. */
export type RosterView = "table" | "cards";

/** Everything loaded by the roster page. */
export interface RosterSnapshot {
  members: RosterMember[];
  invitations: Invitation[];
  assignments: RosterAssignment[];
  stats: RosterStats | null;
}

/** Compact derived summary used by the statistics tiles while loading. */
export interface RosterSummary {
  members: number;
  leads: number;
  available: number;
  pending: number;
  utilisation: number;
}

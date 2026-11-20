/**
 * Deterministic fixtures shared by the roster feature tests.
 */

import type {
  Availability,
  Invitation,
  InvitationStatus,
  RosterAssignment,
  RosterMember,
  RosterRole,
  RosterStats,
} from "./types";

/**
 * Build a roster member.
 *
 * @param overrides - Fields to override.
 * @returns The member fixture.
 */
export function makeMember(
  overrides: Partial<RosterMember> = {},
): RosterMember {
  const displayName = overrides.display_name ?? "Nyx Chandler";
  const role = overrides.role ?? "member";
  const availability = overrides.availability ?? "available";
  return {
    id: "member-1",
    team_id: "team-alpha",
    handle: "nyx",
    display_name: displayName,
    role,
    specialty: "cryptography",
    timezone: "Europe/London",
    availability,
    capacity_hours: 8,
    joined_at: "2026-01-01T10:00:00Z",
    initials: displayName
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase(),
    rank: { observer: 0, analyst: 1, member: 2, lead: 3 }[role],
    availability_label: availability[0].toUpperCase() + availability.slice(1),
    accepts_work: availability === "available",
    ...overrides,
  };
}

/**
 * Build a set of members covering every role and availability.
 *
 * @returns The member fixtures.
 */
export function makeMemberSet(): RosterMember[] {
  const roles: RosterRole[] = ["lead", "member", "analyst", "observer"];
  const states: Availability[] = ["available", "busy", "offline", "available"];
  return roles.map((role, index) =>
    makeMember({
      id: `member-${index + 1}`,
      handle: ["atlas", "nyx", "cipher", "echo"][index],
      display_name: ["Atlas Vale", "Nyx Chandler", "Cipher Fox", "Echo Lin"][
        index
      ],
      role,
      availability: states[index],
      team_id: index === 3 ? "team-beta" : "team-alpha",
    }),
  );
}

/**
 * Build an invitation fixture.
 *
 * @param overrides - Fields to override.
 * @returns The invitation fixture.
 */
export function makeInvitation(
  overrides: Partial<Invitation> = {},
): Invitation {
  const status = overrides.status ?? "pending";
  return {
    id: "invite-1",
    team_id: "team-alpha",
    email: "newcomer@example.com",
    role: "analyst",
    token: "inv_token_123456789",
    status,
    created_at: "2026-01-01T10:00:00Z",
    expires_at: "2099-01-01T10:00:00Z",
    masked_token: "inv_token_123…",
    effective_status: status,
    ...overrides,
  };
}

/**
 * Build a work assignment fixture.
 *
 * @param overrides - Fields to override.
 * @returns The assignment fixture.
 */
export function makeAssignment(
  overrides: Partial<RosterAssignment> = {},
): RosterAssignment {
  return {
    id: "assignment-1",
    member_id: "member-1",
    challenge_id: "challenge-1",
    hours: 3,
    assigned_at: "2026-01-01T11:00:00Z",
    ...overrides,
  };
}

/**
 * Build a statistics fixture.
 *
 * @param overrides - Fields to override.
 * @returns The statistics fixture.
 */
export function makeStats(overrides: Partial<RosterStats> = {}): RosterStats {
  return {
    team_id: null,
    total_members: 4,
    total_capacity_hours: 32,
    assigned_hours: 8,
    assignment_count: 3,
    pending_invitations: 1,
    by_role: { observer: 1, analyst: 1, member: 1, lead: 1 },
    by_availability: { available: 2, busy: 1, offline: 1 },
    utilisation: 0.25,
    utilisation_percent: 25,
    remaining_hours: 24,
    available_count: 2,
    lead_count: 1,
    ...overrides,
  };
}

/**
 * Build an invitation with a specific lifecycle status.
 *
 * @param status - The status to set.
 * @returns The invitation fixture.
 */
export function makeInvitationWithStatus(status: InvitationStatus): Invitation {
  return makeInvitation({ status, effective_status: status });
}

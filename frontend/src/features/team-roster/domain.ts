/**
 * Pure view helpers for the team roster.
 *
 * These functions duplicate no server state: they derive presentation values
 * and client-side filtering from the typed API payloads. Keeping them pure
 * makes the controls deterministic and straightforward to unit test.
 */

import type {
  Availability,
  Invitation,
  InvitationStatus,
  MemberFilters,
  MemberSortKey,
  RosterAssignment,
  RosterMember,
  RosterPermission,
  RosterRole,
  RosterSummary,
  RosterTone,
} from "./types";

/** Ordered role options used by filters, dialogs and role menus. */
export const ROLE_OPTIONS: ReadonlyArray<{
  value: RosterRole;
  label: string;
  description: string;
}> = [
  { value: "observer", label: "Observer", description: "Read-only spectator" },
  {
    value: "analyst",
    label: "Analyst",
    description: "Investigates challenges",
  },
  { value: "member", label: "Member", description: "Full team participant" },
  { value: "lead", label: "Lead", description: "Coordinates the team" },
];

/** Availability options used by filters and status controls. */
export const AVAILABILITY_OPTIONS: ReadonlyArray<{
  value: Availability;
  label: string;
  tone: RosterTone;
}> = [
  { value: "available", label: "Available", tone: "success" },
  { value: "busy", label: "Busy", tone: "warning" },
  { value: "offline", label: "Offline", tone: "neutral" },
];

/** Presentation metadata for every roster role. */
export const ROLE_META: Record<
  RosterRole,
  { label: string; tone: RosterTone; rank: number; short: string }
> = {
  observer: { label: "Observer", tone: "neutral", rank: 0, short: "OBS" },
  analyst: { label: "Analyst", tone: "info", rank: 1, short: "ANL" },
  member: { label: "Member", tone: "accent", rank: 2, short: "MBR" },
  lead: { label: "Lead", tone: "warning", rank: 3, short: "LED" },
};

/** Permissions granted by each role, mirroring the backend role map. */
export const ROLE_PERMISSIONS: Record<RosterRole, readonly RosterPermission[]> =
  {
    observer: ["roster:view", "roster:work"],
    analyst: ["roster:view", "roster:work", "roster:contacts"],
    member: [
      "roster:view",
      "roster:work",
      "roster:contacts",
      "roster:assign",
      "roster:invite",
    ],
    lead: [
      "roster:view",
      "roster:work",
      "roster:contacts",
      "roster:assign",
      "roster:invite",
      "roster:roles",
      "roster:manage",
    ],
  };

/**
 * Derive up to two uppercase initials from a display name.
 *
 * @param name - The display name or handle.
 * @returns The initials, or `??` for an empty name.
 */
export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "??";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

/**
 * Return the seniority rank of a role.
 *
 * @param role - The roster role.
 * @returns A number from zero (observer) to three (lead).
 */
export function roleRank(role: RosterRole): number {
  return ROLE_META[role].rank;
}

/**
 * Return whether a role grants a capability.
 *
 * @param role - The role to inspect.
 * @param permission - The capability to check.
 * @returns Whether the role grants the capability.
 */
export function permits(
  role: RosterRole,
  permission: RosterPermission,
): boolean {
  return ROLE_PERMISSIONS[role].includes(permission);
}

/**
 * Return the display label of an availability state.
 *
 * @param state - The availability state.
 * @returns A human readable label.
 */
export function availabilityLabel(state: Availability): string {
  return (
    AVAILABILITY_OPTIONS.find((option) => option.value === state)?.label ??
    "Unknown"
  );
}

/**
 * Return the semantic tone of an availability state.
 *
 * @param state - The availability state.
 * @returns A design-system colour tone.
 */
export function availabilityTone(state: Availability): RosterTone {
  return (
    AVAILABILITY_OPTIONS.find((option) => option.value === state)?.tone ??
    "neutral"
  );
}

/**
 * Clamp a utilisation ratio into the zero to one range.
 *
 * @param assignedHours - Hours already reserved.
 * @param capacityHours - The member's hour budget.
 * @returns The clamped ratio, or zero for a zero budget.
 */
export function utilisation(
  assignedHours: number,
  capacityHours: number,
): number {
  if (capacityHours <= 0) return 0;
  return Math.min(1, Math.max(0, assignedHours / capacityHours));
}

/**
 * Format an hour count compactly without trailing zeroes.
 *
 * @param hours - The number of hours.
 * @returns A label such as `4.5h`.
 */
export function formatHours(hours: number): string {
  const rounded = Math.round(hours * 10) / 10;
  return `${rounded % 1 === 0 ? rounded.toFixed(0) : rounded.toFixed(1)}h`;
}

/**
 * Return whether an invitation has passed its deadline.
 *
 * @param invitation - The invitation to inspect.
 * @param now - The current timestamp in milliseconds.
 * @returns Whether the invitation is expired.
 */
export function isInvitationExpired(
  invitation: Invitation,
  now: number = Date.now(),
): boolean {
  return Date.parse(invitation.expires_at) <= now;
}

/**
 * Resolve the status an invitation effectively shows to a user.
 *
 * @param invitation - The invitation to inspect.
 * @param now - The current timestamp in milliseconds.
 * @returns The effective status after deadline evaluation.
 */
export function effectiveInvitationStatus(
  invitation: Invitation,
  now: number = Date.now(),
): InvitationStatus {
  if (invitation.status === "pending" && isInvitationExpired(invitation, now)) {
    return "expired";
  }
  return invitation.status;
}

/**
 * Filter members by team, role, availability and free-text query.
 *
 * @param members - The members to filter.
 * @param filters - The active filter values.
 * @returns The matching members in their original order.
 */
export function filterMembers(
  members: RosterMember[],
  filters: MemberFilters,
): RosterMember[] {
  const query = filters.query.trim().toLowerCase();
  return members.filter((member) => {
    if (filters.teamId !== "all" && member.team_id !== filters.teamId)
      return false;
    if (filters.role !== "all" && member.role !== filters.role) return false;
    if (
      filters.availability !== "all" &&
      member.availability !== filters.availability
    ) {
      return false;
    }
    if (!query) return true;
    const haystack = [
      member.handle,
      member.display_name,
      member.specialty,
      member.timezone,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

/**
 * Sort members by a chosen column.
 *
 * @param members - The members to sort.
 * @param key - The sort column.
 * @returns A new sorted array.
 */
export function sortMembers(
  members: RosterMember[],
  key: MemberSortKey,
): RosterMember[] {
  const sorted = [...members];
  switch (key) {
    case "role":
      return sorted.sort(
        (left, right) =>
          roleRank(right.role) - roleRank(left.role) ||
          left.handle.localeCompare(right.handle),
      );
    case "availability":
      return sorted.sort((left, right) => {
        const order = { available: 0, busy: 1, offline: 2 } as const;
        return (
          order[left.availability] - order[right.availability] ||
          left.handle.localeCompare(right.handle)
        );
      });
    case "capacity":
      return sorted.sort(
        (left, right) =>
          left.capacity_hours - right.capacity_hours ||
          left.handle.localeCompare(right.handle),
      );
    case "name":
    default:
      return sorted.sort((left, right) =>
        left.display_name.localeCompare(right.display_name),
      );
  }
}

/**
 * Total the hours assigned to every member.
 *
 * @param assignments - The assignments to aggregate.
 * @returns A map of member identifier to reserved hours.
 */
export function assignedHoursByMember(
  assignments: RosterAssignment[],
): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const assignment of assignments) {
    totals[assignment.member_id] =
      (totals[assignment.member_id] ?? 0) + assignment.hours;
  }
  return totals;
}

/**
 * Derive compact summary values from the currently loaded roster.
 *
 * @param members - The loaded members.
 * @param assignments - The loaded assignments.
 * @param pending - The number of pending invitations.
 * @returns The derived summary.
 */
export function summariseRoster(
  members: RosterMember[],
  assignments: RosterAssignment[],
  pending: number,
): RosterSummary {
  const capacity = members.reduce(
    (sum, member) => sum + member.capacity_hours,
    0,
  );
  const assigned = assignments.reduce(
    (sum, assignment) => sum + assignment.hours,
    0,
  );
  return {
    members: members.length,
    leads: members.filter((member) => member.role === "lead").length,
    available: members.filter((member) => member.availability === "available")
      .length,
    pending,
    utilisation: utilisation(assigned, capacity),
  };
}

/**
 * Validate an email address entered into the invite dialog.
 *
 * @param value - The raw value.
 * @returns Whether the value looks like an email address.
 */
export function isValidInviteEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());
}

/**
 * Validate a handle entered when accepting an invitation or adding a member.
 *
 * @param value - The raw handle.
 * @returns Whether the handle matches the roster naming rules.
 */
export function isValidHandle(value: string): boolean {
  return /^[a-zA-Z0-9][a-zA-Z0-9._-]{1,31}$/.test(value.trim());
}

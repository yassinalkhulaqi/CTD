/**
 * Deterministic test data factories for the dashboard.
 */

import type {
  ActivityEvent,
  Challenge,
  ChallengeCategory,
  ChallengeStatus,
  Difficulty,
  Member,
  MemberRole,
  Presence,
  Team,
} from "../types";

let counter = 0;

/**
 * Return a unique identifier for a test record.
 *
 * @param prefix - The prefix of the identifier.
 * @returns The identifier.
 */
export function nextId(prefix: string): string {
  counter += 1;
  return `${prefix}-${String(counter).padStart(4, "0")}`;
}

/**
 * Build a team.
 *
 * @param overrides - The fields to override.
 * @returns The team.
 */
export function makeTeam(overrides: Partial<Team> = {}): Team {
  return {
    id: nextId("team"),
    name: "RedScribe",
    slug: "redscribe",
    color: "#f43f5e",
    description: "Offensive security specialists.",
    created_at: "2026-01-01T10:00:00Z",
    initials: "RS",
    ...overrides,
  };
}

/**
 * Build a member.
 *
 * @param overrides - The fields to override.
 * @returns The member.
 */
export function makeMember(overrides: Partial<Member> = {}): Member {
  return {
    id: nextId("member"),
    team_id: "team-0001",
    handle: "nyx",
    display_name: "Nyx Chandler",
    role: "analyst" as MemberRole,
    presence: "online" as Presence,
    joined_at: "2026-01-01T10:00:00Z",
    is_online: true,
    ...overrides,
  };
}

/**
 * Build a challenge.
 *
 * @param overrides - The fields to override.
 * @returns The challenge.
 */
export function makeChallenge(overrides: Partial<Challenge> = {}): Challenge {
  return {
    id: nextId("challenge"),
    team_id: "team-0001",
    title: "Nonce Reuse",
    category: "crypto" as ChallengeCategory,
    difficulty: "medium" as Difficulty,
    points: 250,
    description: "The IV looks suspiciously familiar.",
    status: "active" as ChallengeStatus,
    tags: ["aes", "stream-cipher"],
    starts_at: "2026-01-01T10:00:00Z",
    ends_at: "2026-01-01T22:00:00Z",
    created_at: "2026-01-01T10:00:00Z",
    seconds_remaining: 3600,
    ...overrides,
  };
}

/**
 * Build an activity event.
 *
 * @param overrides - The fields to override.
 * @returns The event.
 */
export function makeEvent(overrides: Partial<ActivityEvent> = {}): ActivityEvent {
  counter += 1;
  return {
    id: counter,
    team_id: "team-0001",
    kind: "solve.created",
    payload: { id: 1 },
    occurred_at: "2026-01-01T12:00:00Z",
    ...overrides,
  };
}

/**
 * Build a list of challenges spread across the lifecycle statuses.
 *
 * @param count - The number of challenges.
 * @returns The challenges.
 */
export function makeChallengeSet(count: number): Challenge[] {
  const statuses: ChallengeStatus[] = ["pending", "active", "solved", "locked"];
  return Array.from({ length: count }, (_, index) =>
    makeChallenge({
      title: `Challenge ${index}`,
      status: statuses[index % statuses.length],
    }),
  );
}

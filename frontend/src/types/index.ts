/**
 * Shared domain types mirroring the FastAPI schemas exposed by the dashboard.
 */

export type Difficulty = "trivial" | "easy" | "medium" | "hard" | "insane";

export type ChallengeCategory =
  "web" | "crypto" | "pwn" | "reverse" | "forensics" | "osint" | "misc";

export type ChallengeStatus = "pending" | "active" | "solved" | "locked";

export type MemberRole = "viewer" | "analyst" | "lead" | "admin";

export type Presence = "online" | "away" | "offline";

export type EventKind =
  | "solve.created"
  | "solve.removed"
  | "challenge.created"
  | "challenge.updated"
  | "challenge.deleted"
  | "member.updated"
  | "team.updated"
  | "presence.changed"
  | "heartbeat";

export interface Team {
  id: string;
  name: string;
  slug: string;
  color: string;
  description: string;
  created_at: string;
  initials: string;
}

export interface TeamScore {
  team_id: string;
  team_name: string;
  solves: number;
  points: number;
  challenges: number;
  members: number;
  completion_rate: number;
}

export interface Member {
  id: string;
  team_id: string;
  handle: string;
  display_name: string;
  role: MemberRole;
  presence: Presence;
  joined_at: string;
  is_online: boolean;
}

export interface MemberContribution {
  member_id: string;
  handle: string;
  display_name: string;
  team_id: string;
  solves: number;
  points: number;
  average_points: number;
  first_solve_at: string | null;
  last_solve_at: string | null;
}

export interface Challenge {
  id: string;
  team_id: string;
  title: string;
  category: ChallengeCategory;
  difficulty: Difficulty;
  points: number;
  description: string;
  status: ChallengeStatus;
  tags: string[];
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  seconds_remaining: number;
}

export interface Solve {
  id: string;
  challenge_id: string;
  member_id: string;
  flag: string;
  points_awarded: number;
  solved_at: string;
}

export interface OverviewStats {
  teams: number;
  members: number;
  challenges: number;
  solves: number;
  solved_challenges: number;
  completion_rate: number;
  total_points: number;
  active_members: number;
}

export interface CategoryStats {
  category: ChallengeCategory;
  label: string;
  accent: string;
  challenges: number;
  solves: number;
  solve_rate: number;
  unsolved: number;
}

export interface ActivityEvent {
  id: number;
  team_id: string | null;
  kind: EventKind;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface CompetitionStatus {
  seconds_remaining: number;
  seconds_elapsed: number;
  total_seconds: number;
  progress: number;
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

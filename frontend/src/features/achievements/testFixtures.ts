/**
 * Shared fixtures for achievement feature tests.
 */

import type {
  AchievementStats,
  Badge,
  BadgeView,
  LeaderboardEntry,
} from "./types";

/** Build a badge definition for tests. */
export function makeBadge(overrides: Partial<Badge> = {}): Badge {
  return {
    id: "first-blood",
    name: "First Blood",
    description: "Solve your first challenge",
    tier: "bronze",
    criteria_kind: "solves",
    criteria_value: 1,
    icon: "target",
    points: 10,
    secret: false,
    score: 10,
    target: 1,
    tier_rank: 1,
    criteria_label: "First solve",
    metric_key: "solves",
    ...overrides,
  };
}

/** Build a presentation-ready badge for tests. */
export function makeBadgeView(overrides: Partial<BadgeView> = {}): BadgeView {
  const badge = overrides.badge ?? makeBadge();
  return {
    badge,
    awarded: false,
    revealed: true,
    rarity: 72,
    holders: 4,
    current: 0,
    target: badge.target,
    percent: 0,
    rarity_band: "uncommon",
    status: "locked",
    display_name: badge.name,
    display_description: badge.description,
    display_icon: badge.icon,
    ...overrides,
  };
}

/** Build aggregate statistics for tests. */
export function makeStats(
  overrides: Partial<AchievementStats> = {},
): AchievementStats {
  return {
    badges: 16,
    awards: 42,
    members_with_awards: 9,
    members: 12,
    points: 1280,
    secret_badges: 3,
    gold_badges: 2,
    recent_awards: 5,
    average_rarity: 68,
    participation_rate: 75,
    completion_rate: 32,
    points_per_member: 107,
    ...overrides,
  };
}

/** Build a leaderboard row for tests. */
export function makeLeaderboardEntry(
  overrides: Partial<LeaderboardEntry> = {},
): LeaderboardEntry {
  return {
    member_id: "member-1",
    handle: "nova",
    display_name: "Nova",
    label: "Nova (@nova)",
    awards: 8,
    points: 320,
    rank: 1,
    rarity: 74,
    ...overrides,
  };
}

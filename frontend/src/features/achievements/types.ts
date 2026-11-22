/**
 * Domain types and pure presentation helpers for the achievement feature.
 */

/** Prestige tiers understood by the badge engine. */
export type BadgeTier = "bronze" | "silver" | "gold";

/** Metric families used by badge criteria. */
export type CriteriaKind = "solves" | "categories" | "streak" | "hints";

/** Display status of a badge relative to the current viewer. */
export type BadgeStatus = "unlocked" | "ready" | "locked";

/** Rarity band derived from the rarity score. */
export type RarityBand = "legendary" | "rare" | "uncommon" | "common";

/** A badge definition returned by the API. */
export interface Badge {
  id: string;
  name: string;
  description: string;
  tier: BadgeTier;
  criteria_kind: CriteriaKind;
  criteria_value: number;
  icon: string;
  points: number;
  secret: boolean;
  score: number;
  target: number;
  tier_rank: number;
  criteria_label: string;
  metric_key: string;
}

/** A member's progress towards a single badge. */
export interface AchievementProgress {
  member_id: string;
  badge_id: string;
  current: number;
  target: number;
  percent: number;
  remaining: number;
  is_complete: boolean;
}

/** An immutable award record. */
export interface AchievementAward {
  id: string;
  badge_id: string;
  member_id: string;
  awarded_at: string;
  evidence: Record<string, unknown>;
  observed_value: number;
  is_fresh: boolean;
}

/** A badge prepared for presentation to the current viewer. */
export interface BadgeView {
  badge: Badge;
  awarded: boolean;
  revealed: boolean;
  rarity: number;
  holders: number;
  current: number;
  target: number;
  percent: number;
  rarity_band: RarityBand;
  status: BadgeStatus;
  display_name: string;
  display_description: string;
  display_icon: string;
}

/** Response returned by the badge catalogue endpoints. */
export interface BadgeListResponse {
  badges: BadgeView[];
  total: number;
  tier: BadgeTier | null;
  criteria_kind: CriteriaKind | null;
}

/** Response returned by the badge detail endpoint. */
export interface BadgeDetailResponse {
  badge: BadgeView;
  awarded_to: number;
}

/** One badge evaluation outcome. */
export interface EvaluationOutcome {
  badge_id: string;
  member_id: string;
  current: number;
  target: number;
  percent: number;
  qualifies: boolean;
  remaining: number;
  status: string;
  criteria_kind: CriteriaKind;
  tier: BadgeTier;
  awarded: boolean;
  newly_awarded: boolean;
  reason: string;
}

/** Result of evaluating one member. */
export interface EvaluationResult {
  member_id: string;
  metrics: Record<string, number>;
  evaluated: number;
  eligible: number;
  unlocked: number;
  outcomes: EvaluationOutcome[];
}

/** Result of evaluating several members. */
export interface BatchEvaluationResult {
  results: EvaluationResult[];
  evaluated_members: number;
  total_unlocked: number;
}

/** One row of the achievement leaderboard. */
export interface LeaderboardEntry {
  member_id: string;
  handle: string;
  display_name: string;
  label: string;
  awards: number;
  points: number;
  rank: number;
  rarity: number;
}

/** Leaderboard response payload. */
export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total: number;
}

/** Aggregate achievement counters. */
export interface AchievementStats {
  badges: number;
  awards: number;
  members_with_awards: number;
  members: number;
  points: number;
  secret_badges: number;
  gold_badges: number;
  recent_awards: number;
  average_rarity: number;
  participation_rate: number;
  completion_rate: number;
  points_per_member: number;
}

/** Full achievement profile of a member. */
export interface MemberAchievement {
  member_id: string;
  points: number;
  unlocked: number;
  completion: number;
  next_badge: BadgeView | null;
  awards: AchievementAward[];
  progress: AchievementProgress[];
  badges: BadgeView[];
}

/** Result of a manual badge grant. */
export interface AwardResult {
  badge: Badge;
  award: AchievementAward;
  awarded: boolean;
  progress: number | null;
}

/** Payload used to create a custom badge. */
export interface BadgeCreatePayload {
  name: string;
  description?: string;
  tier: BadgeTier;
  criteria_kind: CriteriaKind;
  criteria_value: number;
  icon?: string;
  points?: number;
  secret?: boolean;
}

/** Query accepted by the catalogue endpoint. */
export interface BadgeListParams {
  member_id?: string;
  tier?: BadgeTier;
  criteria_kind?: CriteriaKind;
  include_secret?: boolean;
}

/** Result of seeding the built-in catalogue. */
export interface SeedResult {
  created: number;
  total: number;
}

/** Order of tiers from least to most prestigious. */
export const TIER_ORDER: BadgeTier[] = ["bronze", "silver", "gold"];

/** Order of criteria kinds as shown in filter controls. */
export const CRITERIA_ORDER: CriteriaKind[] = [
  "solves",
  "categories",
  "streak",
  "hints",
];

const TIER_COLORS: Record<BadgeTier, string> = {
  bronze: "#d08b5b",
  silver: "#b8c4d4",
  gold: "#f5c451",
};

const RARITY_TONES: Record<RarityBand, string> = {
  legendary: "#f5c451",
  rare: "#c084fc",
  uncommon: "#38bdf8",
  common: "#94a3b8",
};

/**
 * Clamp a numeric value to an inclusive interval.
 *
 * @param value - The input value.
 * @param lower - Lower bound.
 * @param upper - Upper bound.
 * @returns The clamped value.
 */
export function clamp(value: number, lower: number, upper: number): number {
  return Math.min(Math.max(value, lower), upper);
}

/**
 * Convert a percentage into a 0-1 ratio.
 *
 * @param percent - A percentage between 0 and 100.
 * @returns The clamped ratio.
 */
export function progressRatio(percent: number): number {
  return clamp(percent, 0, 100) / 100;
}

/**
 * Return the accent colour of a tier.
 *
 * @param tier - The badge tier.
 * @returns A CSS colour string.
 */
export function tierColor(tier: BadgeTier): string {
  return TIER_COLORS[tier];
}

/**
 * Return the numeric rank of a tier.
 *
 * @param tier - The badge tier.
 * @returns A one-based rank.
 */
export function tierRank(tier: BadgeTier): number {
  return TIER_ORDER.indexOf(tier) + 1;
}

/**
 * Return the accent colour of a rarity band.
 *
 * @param band - The rarity band.
 * @returns A CSS colour string.
 */
export function rarityColor(band: RarityBand): string {
  return RARITY_TONES[band];
}

/**
 * Build a concise criteria caption for a badge.
 *
 * @param badge - The badge definition.
 * @returns A human readable caption.
 */
export function criteriaCaption(badge: Badge): string {
  if (badge.criteria_kind === "hints") {
    return `At most ${badge.criteria_value} hints`;
  }
  if (badge.criteria_kind === "streak") {
    return `${badge.criteria_value} day streak`;
  }
  if (badge.criteria_kind === "categories") {
    return `${badge.criteria_value} categories`;
  }
  return `${badge.criteria_value} solves`;
}

/**
 * Sort badge views by tier, status and name for a stable gallery order.
 *
 * @param badges - The badge views to sort.
 * @returns A new sorted array.
 */
export function sortBadges(badges: BadgeView[]): BadgeView[] {
  return [...badges].sort((a, b) => {
    if (a.awarded !== b.awarded) return a.awarded ? -1 : 1;
    const tierDifference = tierRank(b.badge.tier) - tierRank(a.badge.tier);
    if (tierDifference !== 0) return tierDifference;
    const percentDifference = b.percent - a.percent;
    if (percentDifference !== 0) return percentDifference;
    return a.badge.name.localeCompare(b.badge.name);
  });
}

/**
 * Filter badge views by tier, criterion and search text.
 *
 * @param badges - The full badge collection.
 * @param tier - Optional tier filter, or `all`.
 * @param kind - Optional criterion filter, or `all`.
 * @param query - Optional free-text query.
 * @returns Matching badge views.
 */
export function filterBadges(
  badges: BadgeView[],
  tier: BadgeTier | "all",
  kind: CriteriaKind | "all",
  query = "",
): BadgeView[] {
  const needle = query.trim().toLowerCase();
  return badges.filter((view) => {
    if (tier !== "all" && view.badge.tier !== tier) return false;
    if (kind !== "all" && view.badge.criteria_kind !== kind) return false;
    if (!needle) return true;
    return (
      view.display_name.toLowerCase().includes(needle) ||
      view.display_description.toLowerCase().includes(needle) ||
      view.badge.criteria_label.toLowerCase().includes(needle)
    );
  });
}

/**
 * Group badge views by prestige tier.
 *
 * @param badges - The badge views to group.
 * @returns A mapping from tier to its badges.
 */
export function groupByTier(
  badges: BadgeView[],
): Record<BadgeTier, BadgeView[]> {
  const grouped: Record<BadgeTier, BadgeView[]> = {
    bronze: [],
    silver: [],
    gold: [],
  };
  for (const view of badges) grouped[view.badge.tier].push(view);
  return grouped;
}

/**
 * Choose the closest unearned badge for a member.
 *
 * @param badges - The badge collection.
 * @returns The next badge, when one exists.
 */
export function nextBadge(badges: BadgeView[]): BadgeView | null {
  const candidates = badges.filter((view) => !view.awarded);
  if (candidates.length === 0) return null;
  return candidates.reduce((best, view) =>
    view.percent > best.percent ? view : best,
  );
}

/**
 * Sum the tier-adjusted score of unlocked badges.
 *
 * @param badges - The badge collection.
 * @returns The total points earned.
 */
export function unlockedPoints(badges: BadgeView[]): number {
  return badges.reduce(
    (total, view) => total + (view.awarded ? view.badge.score : 0),
    0,
  );
}

/**
 * Count badges by status.
 *
 * @param badges - The badge collection.
 * @returns Counts for unlocked, ready and locked badges.
 */
export function statusCounts(badges: BadgeView[]): Record<BadgeStatus, number> {
  const counts: Record<BadgeStatus, number> = {
    unlocked: 0,
    ready: 0,
    locked: 0,
  };
  for (const view of badges) counts[view.status] += 1;
  return counts;
}

/**
 * Format an ISO timestamp as a short relative label.
 *
 * @param iso - The ISO-8601 timestamp.
 * @param now - Optional reference time in milliseconds.
 * @returns A relative label such as `3d ago`.
 */
export function relativeTime(iso: string, now = Date.now()): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "unknown";
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/**
 * Format a percentage with a single decimal when needed.
 *
 * @param percent - The percentage value.
 * @returns A display-ready label.
 */
export function percentLabel(percent: number): string {
  const safe = clamp(percent, 0, 100);
  return Number.isInteger(safe) ? `${safe}%` : `${safe.toFixed(1)}%`;
}

/**
 * Resolve the icon shown on a badge, masking secrets when necessary.
 *
 * @param view - The badge view.
 * @returns A lucide-compatible icon name.
 */
export function iconName(view: BadgeView): string {
  if (!view.revealed) return "CircleHelp";
  const known = [
    "award",
    "brain",
    "calendar",
    "crown",
    "flame",
    "gem",
    "layers",
    "moon",
    "shield",
    "sparkles",
    "swords",
    "target",
  ];
  if (known.includes(view.display_icon)) return view.display_icon;
  return "Trophy";
}

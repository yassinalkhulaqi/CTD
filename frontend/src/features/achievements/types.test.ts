import { describe, expect, it } from "vitest";
import { makeBadge, makeBadgeView } from "./testFixtures";
import {
  clamp,
  criteriaCaption,
  filterBadges,
  groupByTier,
  iconName,
  nextBadge,
  percentLabel,
  progressRatio,
  relativeTime,
  sortBadges,
  statusCounts,
  tierColor,
  tierRank,
  unlockedPoints,
} from "./types";

describe("achievement presentation helpers", () => {
  it("clamps percentages and converts them to ratios", () => {
    expect(clamp(140, 0, 100)).toBe(100);
    expect(clamp(-10, 0, 100)).toBe(0);
    expect(progressRatio(45)).toBeCloseTo(0.45);
    expect(progressRatio(250)).toBe(1);
  });

  it("formats percentage labels without noisy decimals", () => {
    expect(percentLabel(42)).toBe("42%");
    expect(percentLabel(42.456)).toBe("42.5%");
    expect(percentLabel(-4)).toBe("0%");
  });

  it("maps tiers and rarity bands to colours and ranks", () => {
    expect(tierRank("bronze")).toBe(1);
    expect(tierRank("gold")).toBe(3);
    expect(tierColor("gold")).toBe("#f5c451");
  });

  it("describes each criterion family", () => {
    expect(
      criteriaCaption(
        makeBadge({ criteria_kind: "solves", criteria_value: 5 }),
      ),
    ).toBe("5 solves");
    expect(
      criteriaCaption(
        makeBadge({ criteria_kind: "categories", criteria_value: 3 }),
      ),
    ).toBe("3 categories");
    expect(
      criteriaCaption(
        makeBadge({ criteria_kind: "streak", criteria_value: 7 }),
      ),
    ).toBe("7 day streak");
    expect(
      criteriaCaption(makeBadge({ criteria_kind: "hints", criteria_value: 2 })),
    ).toBe("At most 2 hints");
  });

  it("sorts unlocked badges first, then by tier and progress", () => {
    const lockedGold = makeBadgeView({
      badge: makeBadge({ id: "gold", tier: "gold" }),
      percent: 80,
    });
    const readyBronze = makeBadgeView({
      badge: makeBadge({ id: "bronze", tier: "bronze" }),
      percent: 60,
      status: "ready",
    });
    const unlockedSilver = makeBadgeView({
      badge: makeBadge({ id: "silver", tier: "silver" }),
      awarded: true,
      status: "unlocked",
    });
    expect(
      sortBadges([lockedGold, readyBronze, unlockedSilver]).map(
        (view) => view.badge.id,
      ),
    ).toEqual(["silver", "gold", "bronze"]);
  });

  it("filters by tier, criterion and free text", () => {
    const badges = [
      makeBadgeView({ badge: makeBadge({ id: "solver", tier: "bronze" }) }),
      makeBadgeView({
        badge: makeBadge({
          id: "streaker",
          name: "Hot Streak",
          tier: "gold",
          criteria_kind: "streak",
          criteria_label: "Hot streak",
        }),
      }),
    ];
    expect(filterBadges(badges, "gold", "all", "")).toHaveLength(1);
    expect(filterBadges(badges, "all", "streak", "")).toHaveLength(1);
    expect(filterBadges(badges, "all", "all", "first solve")).toEqual([
      badges[0],
    ]);
    expect(filterBadges(badges, "all", "all", "unknown")).toEqual([]);
  });

  it("groups badges by tier and counts statuses", () => {
    const badges = [
      makeBadgeView({ badge: makeBadge({ id: "a", tier: "bronze" }) }),
      makeBadgeView({
        badge: makeBadge({ id: "b", tier: "silver" }),
        status: "ready",
      }),
      makeBadgeView({
        badge: makeBadge({ id: "c", tier: "gold" }),
        awarded: true,
        status: "unlocked",
      }),
    ];
    const grouped = groupByTier(badges);
    expect(grouped.bronze).toHaveLength(1);
    expect(grouped.silver[0].badge.id).toBe("b");
    expect(grouped.gold).toHaveLength(1);
    expect(statusCounts(badges)).toEqual({ unlocked: 1, ready: 1, locked: 1 });
  });

  it("picks the closest badge and sums unlocked points", () => {
    const near = makeBadgeView({
      badge: makeBadge({ score: 20 }),
      percent: 90,
    });
    const far = makeBadgeView({
      badge: makeBadge({ id: "far", score: 50 }),
      percent: 10,
      awarded: true,
      status: "unlocked",
    });
    expect(nextBadge([far, near])?.badge.id).toBe(near.badge.id);
    expect(nextBadge([far])).toBeNull();
    expect(unlockedPoints([near, far])).toBe(50);
  });

  it("formats relative timestamps and resolves icons", () => {
    const now = Date.parse("2026-01-10T12:00:00Z");
    expect(relativeTime("2026-01-10T11:59:30Z", now)).toBe("just now");
    expect(relativeTime("2026-01-10T11:00:00Z", now)).toBe("1h ago");
    expect(relativeTime("not-a-date", now)).toBe("unknown");
    expect(iconName(makeBadgeView())).toBe("target");
    expect(iconName(makeBadgeView({ revealed: false }))).toBe("CircleHelp");
  });
});

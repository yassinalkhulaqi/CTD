import { describe, expect, it } from "vitest";
import {
  budgetUsage,
  canUnlock,
  costCurve,
  formatCountdown,
  formatCredits,
  maskHintContent,
  ringGeometry,
  roundCredits,
  stateTone,
  tierCost,
} from "./hints";
import type { HintBudget, HintView } from "./types";

function budget(overrides: Partial<HintBudget> = {}): HintBudget {
  return {
    team_id: "team-1",
    total: 600,
    spent: 100,
    remaining: 500,
    reset_at: "2026-01-08T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    utilization: 100 / 600,
    is_exhausted: false,
    ...overrides,
  };
}

function view(overrides: Partial<HintView> = {}): HintView {
  return {
    hint_id: "hint-1",
    challenge_id: "challenge-1",
    tier: 1,
    title: "Look at the header",
    content: "A" + "*".repeat(40),
    cost: 25,
    reveal_after_seconds: 0,
    is_active: true,
    state: "eligible",
    reason: "Ready to unlock",
    remaining_seconds: 0,
    required_tier: null,
    unlocked: false,
    eligible: true,
    badge_label: "Available",
    unlocked_at: null,
    unlocked_by: null,
    ...overrides,
  };
}

describe("hint cost curve", () => {
  it("applies the geometric multiplier and rounds half up", () => {
    expect(tierCost(25, 2, 1)).toBe(25);
    expect(tierCost(25, 2, 2)).toBe(50);
    expect(tierCost(25, 2, 3)).toBe(100);
    expect(tierCost(10, 1.5, 3)).toBe(23);
    expect(roundCredits(22.5)).toBe(23);
  });

  it("produces cumulative points for all three tiers", () => {
    const curve = costCurve(10, 1.5);
    expect(curve.map((point) => point.cost)).toEqual([10, 15, 23]);
    expect(curve.map((point) => point.cumulative)).toEqual([10, 25, 48]);
    expect(curve[2].label).toBe("T3: 23");
    expect(costCurve(10, 2, 5)).toHaveLength(3);
  });

  it("clamps invalid inputs to a safe ladder", () => {
    expect(tierCost(0, 0.5, 9)).toBe(1);
    expect(tierCost(10, 1.5, 0)).toBe(10);
    expect(roundCredits(Number.NaN)).toBe(0);
  });
});

describe("hint presentation helpers", () => {
  it("masks locked content without changing its length", () => {
    const masked = maskHintContent("The secret is in the footer", 7);
    expect(masked.startsWith("The sec")).toBe(true);
    expect(masked).toHaveLength("The secret is in the footer".length);
    expect(maskHintContent("short", 28)).toBe("short");
  });

  it("computes budget usage and ring geometry", () => {
    expect(budgetUsage(budget()).remaining).toBe(500);
    expect(budgetUsage(null).total).toBe(0);
    expect(budgetUsage(budget({ total: 100, spent: 150 })).remaining).toBe(0);
    const geometry = ringGeometry(0.25, 100, 10);
    expect(geometry.radius).toBe(45);
    expect(geometry.percent).toBe(25);
    expect(geometry.offset).toBeCloseTo(geometry.circumference * 0.75);
    expect(ringGeometry(4, 100, 10).percent).toBe(100);
  });

  it("gates unlocks and formats supporting labels", () => {
    expect(canUnlock(view(), budget())).toBe(true);
    expect(canUnlock(view(), null)).toBe(false);
    expect(
      canUnlock(view({ state: "locked", eligible: false }), budget()),
    ).toBe(false);
    expect(canUnlock(view({ cost: 900 }), budget())).toBe(false);
    expect(stateTone("unlocked")).toBe("success");
    expect(stateTone("exhausted")).toBe("danger");
    expect(formatCountdown(0)).toBe("Ready");
    expect(formatCountdown(45)).toBe("45s");
    expect(formatCountdown(125)).toBe("2m 5s");
    expect(formatCountdown(7200)).toBe("2h 0m");
    expect(formatCredits(1234)).toBe("1,234");
  });
});

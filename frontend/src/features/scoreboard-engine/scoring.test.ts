import { describe, expect, it } from "vitest";
import {
  DIFFICULTY_WEIGHTS,
  computeSolvePoints,
  decayFor,
  formatScore,
  movementDescription,
  movementLabel,
  podiumTone,
  projectStreak,
  sparklinePoints,
  validateRule,
} from "./scoring";
import type { ScoreRuleDraft } from "./types";

function rule(overrides: Partial<ScoreRuleDraft> = {}): ScoreRuleDraft {
  return {
    name: "Balanced",
    base_points: 100,
    difficulty_multiplier: 1,
    first_blood_bonus: 50,
    hint_penalty: 10,
    decay_factor: 0.9,
    decay_enabled: true,
    ...overrides,
  };
}

describe("scoreboard scoring math", () => {
  it("applies difficulty weights and the multiplier", () => {
    expect(DIFFICULTY_WEIGHTS.hard).toBe(3);
    expect(computeSolvePoints(rule({ difficulty_multiplier: 2 }), "easy")).toBe(
      200,
    );
    expect(computeSolvePoints(rule({ difficulty_multiplier: 2 }), "hard")).toBe(
      600,
    );
  });

  it("decays later solves and clamps negative awards to zero", () => {
    expect(decayFor(rule({ decay_factor: 0.5 }), 2)).toBe(0.25);
    expect(computeSolvePoints(rule(), "easy", 2)).toBe(81);
    expect(
      computeSolvePoints(rule({ hint_penalty: 500 }), "easy", 0, false, 2),
    ).toBe(0);
  });

  it("adds first blood bonuses and subtracts hint penalties", () => {
    expect(computeSolvePoints(rule(), "easy", 0, true)).toBe(150);
    expect(computeSolvePoints(rule(), "easy", 0, false, 3)).toBe(70);
  });

  it("projects a streak with a first blood on the opening solve", () => {
    expect(
      projectStreak(rule({ decay_enabled: false }), ["easy", "easy"]),
    ).toEqual([150, 100]);
  });

  it("validates rule values with precise messages", () => {
    expect(validateRule(rule())).toEqual({});
    const errors = validateRule(
      rule({
        name: " ",
        base_points: -1,
        difficulty_multiplier: 12,
        decay_factor: 2,
      }),
    );
    expect(errors.name).toBeTruthy();
    expect(errors.base_points).toContain("negative");
    expect(errors.difficulty_multiplier).toContain("10");
    expect(errors.decay_factor).toContain("1");
  });
});

describe("scoreboard presentation helpers", () => {
  it("formats movement labels and descriptions", () => {
    expect(movementLabel("up", 2)).toBe("↑2");
    expect(movementLabel("down", 1)).toBe("↓1");
    expect(movementLabel("stable")).toBe("—");
    expect(movementLabel("new")).toBe("NEW");
    expect(movementDescription("up", 1)).toBe("Climbed 1 position");
    expect(movementDescription("down", 3)).toBe("Fell 3 positions");
  });

  it("builds sparkline coordinates including flat series", () => {
    expect(sparklinePoints([])).toBe("");
    expect(sparklinePoints([5])).toBe("120,30");
    const points = sparklinePoints([10, 20, 30], 100, 50).split(" ");
    expect(points).toHaveLength(3);
    expect(points[0]).toBe("0.0,44.0");
    expect(points[2]).toBe("100.0,6.0");
  });

  it("formats scores and podium tones", () => {
    expect(formatScore(12345.6)).toBe("12,346");
    expect(podiumTone(1)).toBe("gold");
    expect(podiumTone(4)).toBe("neutral");
  });
});

/** Pure logic tests for event status, countdowns and aggregates. */

import { describe, expect, it } from "vitest";
import {
  aggregateStats,
  capacityLabel,
  countdownSeconds,
  deriveEventStatus,
  formatCountdown,
  ringProgress,
  statusTone,
} from "./utils";
import type { CtfEvent, EventStats } from "./types";

const start = "2026-06-01T12:00:00.000Z";
const end = "2026-06-02T12:00:00.000Z";
const at = (iso: string) => Date.parse(iso);

function schedule(
  status: "draft" | "upcoming" | "live" | "archived" = "upcoming",
) {
  return { starts_at: start, ends_at: end, status };
}

describe("deriveEventStatus", () => {
  it("derives upcoming, live and archived from the window", () => {
    expect(deriveEventStatus(schedule(), at("2026-06-01T11:59:59.000Z"))).toBe(
      "upcoming",
    );
    expect(deriveEventStatus(schedule(), at(start))).toBe("live");
    expect(deriveEventStatus(schedule(), at("2026-06-02T11:59:59.000Z"))).toBe(
      "live",
    );
    expect(deriveEventStatus(schedule(), at(end))).toBe("archived");
  });

  it("preserves explicit draft and archived states", () => {
    expect(deriveEventStatus(schedule("draft"), at(start))).toBe("draft");
    expect(
      deriveEventStatus(schedule("archived"), at("2026-05-01T00:00:00.000Z")),
    ).toBe("archived");
  });
});

describe("formatCountdown", () => {
  it("clamps negative values and formats seconds", () => {
    expect(formatCountdown(-12)).toBe("00m 00s");
    expect(formatCountdown(0)).toBe("00m 00s");
    expect(formatCountdown(9)).toBe("00m 09s");
    expect(formatCountdown(729)).toBe("12m 09s");
  });

  it("switches to hours and days at the right thresholds", () => {
    expect(formatCountdown(5 * 3600 + 32 * 60)).toBe("05h 32m");
    expect(formatCountdown(2 * 86400 + 4 * 3600)).toBe("02d 04h");
  });
});

describe("countdownSeconds and ringProgress", () => {
  it("counts down to the start before the event opens", () => {
    const now = at("2026-06-01T11:00:00.000Z");
    expect(countdownSeconds(schedule(), now)).toBe(3600);
    expect(ringProgress(schedule(), now)).toBeGreaterThan(0);
    expect(ringProgress(schedule(), now)).toBeLessThanOrEqual(1);
  });

  it("counts down to the end while live and clamps afterwards", () => {
    const now = at("2026-06-01T18:00:00.000Z");
    expect(countdownSeconds(schedule(), now)).toBe(18 * 3600);
    expect(ringProgress(schedule(), now)).toBeCloseTo(0.25, 5);
    expect(countdownSeconds(schedule(), at(end + 1000))).toBe(0);
    expect(countdownSeconds(schedule("draft"), now)).toBe(0);
  });
});

describe("presentation helpers", () => {
  it("maps statuses to badge tones", () => {
    expect(statusTone("draft")).toBe("neutral");
    expect(statusTone("upcoming")).toBe("info");
    expect(statusTone("live")).toBe("success");
    expect(statusTone("archived")).toBe("warning");
  });

  it("aggregates statistics", () => {
    const stats: EventStats[] = [
      {
        event_id: "1",
        capacity: 10,
        confirmed: 5,
        waitlisted: 2,
        cancelled: 0,
        promotions: 0,
        total: 7,
        available_slots: 5,
        is_full: false,
        capacity_ratio: 0.5,
        fill_percentage: 50,
        waitlist_pressure: 0.2,
      },
      {
        event_id: "2",
        capacity: 10,
        confirmed: 15,
        waitlisted: 0,
        cancelled: 1,
        promotions: 1,
        total: 16,
        available_slots: 0,
        is_full: true,
        capacity_ratio: 1.5,
        fill_percentage: 100,
        waitlist_pressure: 0,
      },
    ];
    expect(aggregateStats(stats)).toEqual({
      events: 2,
      confirmed: 20,
      waitlisted: 2,
      fill: 100,
    });
    expect(aggregateStats([]).fill).toBe(0);
  });

  it("formats the capacity label", () => {
    const event = { max_team_size: 8 } as CtfEvent;
    expect(capacityLabel(event)).toBe("0 / 8 teams");
    expect(capacityLabel(event, { confirmed: 3 } as EventStats)).toBe(
      "3 / 8 teams",
    );
  });
});

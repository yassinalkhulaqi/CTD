import { describe, expect, it } from "vitest";
import {
  clamp,
  cn,
  formatCompactDuration,
  formatDuration,
  formatNumber,
  formatPercent,
  formatRelativeTime,
  formatTime,
  uniqueId,
} from "../lib/utils";

describe("cn", () => {
  it("joins string class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("ignores falsy values", () => {
    expect(cn("a", false, null, undefined, 0)).toBe("a");
  });

  it("keeps truthy keys of an object", () => {
    expect(cn({ a: true, b: false })).toBe("a");
  });
});

describe("clamp", () => {
  it("keeps values inside the range", () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-1, 0, 10)).toBe(0);
    expect(clamp(42, 0, 10)).toBe(10);
  });
});

describe("formatNumber", () => {
  it("adds thousands separators", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });
});

describe("formatDuration", () => {
  it("formats seconds as HH:MM:SS", () => {
    expect(formatDuration(3661)).toBe("01:01:01");
  });

  it("clamps negative durations", () => {
    expect(formatDuration(-10)).toBe("00:00:00");
  });
});

describe("formatCompactDuration", () => {
  it("uses seconds below a minute", () => {
    expect(formatCompactDuration(45)).toBe("45s");
  });

  it("uses minutes below an hour", () => {
    expect(formatCompactDuration(150)).toBe("2m 30s");
  });

  it("uses hours below a day", () => {
    expect(formatCompactDuration(7_200)).toBe("2h 0m");
  });

  it("uses days beyond a day", () => {
    expect(formatCompactDuration(90_000)).toBe("1d 1h");
  });
});

describe("formatRelativeTime", () => {
  const now = new Date("2026-01-01T12:00:00Z");

  it("reports recent timestamps as just now", () => {
    expect(formatRelativeTime("2026-01-01T11:59:40Z", now)).toBe("just now");
  });

  it("reports minutes in the past", () => {
    expect(formatRelativeTime("2026-01-01T11:45:00Z", now)).toBe(
      "15 minutes ago",
    );
  });

  it("returns a dash for invalid timestamps", () => {
    expect(formatRelativeTime("not-a-date", now)).toBe("—");
  });
});

describe("formatTime", () => {
  it("formats a timestamp as wall clock time", () => {
    expect(formatTime("2026-01-01T12:34:56Z")).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it("returns a dash for invalid timestamps", () => {
    expect(formatTime("nope")).toBe("—");
  });
});

describe("formatPercent", () => {
  it("formats a ratio as a percentage", () => {
    expect(formatPercent(0.456)).toBe("45.6%");
  });

  it("clamps out of range ratios", () => {
    expect(formatPercent(2)).toBe("100.0%");
    expect(formatPercent(-1)).toBe("0.0%");
  });
});

describe("uniqueId", () => {
  it("prefixes generated identifiers", () => {
    expect(uniqueId("row").startsWith("row-")).toBe(true);
  });

  it("generates different identifiers", () => {
    expect(uniqueId()).not.toBe(uniqueId());
  });
});

import { describe, expect, it } from "vitest";
import {
  buildAreaPath,
  buildBands,
  buildSmoothPath,
  heatColour,
  hourLabel,
  linearTicks,
  maxOf,
  minOf,
  niceCeiling,
  percent,
  scaleY,
  weekdayLabel,
} from "./chartUtils";

describe("maxOf", () => {
  it("returns the largest value", () => {
    expect(maxOf([1, 9, 4])).toBe(9);
  });

  it("returns the fallback for an empty series", () => {
    expect(maxOf([], 3)).toBe(3);
  });
});

describe("minOf", () => {
  it("returns the smallest value", () => {
    expect(minOf([4, 2, 8])).toBe(2);
  });
});

describe("niceCeiling", () => {
  it("rounds the bound up to a readable value", () => {
    expect(niceCeiling(7)).toBe(10);
    expect(niceCeiling(120)).toBe(200);
    expect(niceCeiling(3)).toBe(5);
  });

  it("never returns a bound below one", () => {
    expect(niceCeiling(0)).toBe(1);
    expect(niceCeiling(-4)).toBe(1);
  });
});

describe("linearTicks", () => {
  it("includes both bounds", () => {
    const ticks = linearTicks(10, 4);
    expect(ticks[0]).toBe(0);
    expect(ticks[ticks.length - 1]).toBe(10);
  });

  it("returns a single tick for a zero bound", () => {
    expect(linearTicks(0)).toEqual([0]);
  });
});

describe("scaleY", () => {
  it("maps the maximum to the top of the chart", () => {
    expect(scaleY(10, 10, 100)).toBe(0);
  });

  it("maps the minimum to the bottom of the chart", () => {
    expect(scaleY(0, 10, 100)).toBe(100);
  });

  it("accounts for the bottom padding", () => {
    expect(scaleY(0, 10, 100, 20)).toBe(80);
  });
});

describe("buildBands", () => {
  it("creates one band per category", () => {
    const bands = buildBands(4, 100);
    expect(bands).toHaveLength(4);
    expect(bands[0].start).toBeGreaterThan(0);
    expect(bands[3].start + bands[3].width).toBeLessThan(100);
  });

  it("returns nothing for an empty series", () => {
    expect(buildBands(0, 100)).toEqual([]);
  });
});

describe("buildSmoothPath", () => {
  it("returns an empty path without points", () => {
    expect(buildSmoothPath([])).toBe("");
  });

  it("builds a move command for a single point", () => {
    expect(buildSmoothPath([{ x: 1, y: 2 }])).toBe("M 1 2");
  });

  it("builds a curve through every point", () => {
    const path = buildSmoothPath([
      { x: 0, y: 0 },
      { x: 10, y: 20 },
      { x: 20, y: 5 },
    ]);
    expect(path.startsWith("M 0 0")).toBe(true);
    expect(path.split("C")).toHaveLength(3);
  });
});

describe("buildAreaPath", () => {
  it("closes the path on the baseline", () => {
    const path = buildAreaPath(
      [
        { x: 0, y: 10 },
        { x: 10, y: 20 },
      ],
      50,
    );
    expect(path.endsWith("Z")).toBe(true);
    expect(path).toContain("50");
  });
});

describe("hourLabel", () => {
  it("labels the trailing hours", () => {
    expect(hourLabel(23, 24, 23)).toBe("23:00");
    expect(hourLabel(0, 24, 23)).toBe("00:00");
  });
});

describe("weekdayLabel", () => {
  it("labels the weekdays", () => {
    expect(weekdayLabel(0)).toBe("Mon");
    expect(weekdayLabel(6)).toBe("Sun");
  });
});

describe("percent", () => {
  it("formats a ratio", () => {
    expect(percent(0.456)).toBe("46%");
  });

  it("clamps the ratio", () => {
    expect(percent(2)).toBe("100%");
    expect(percent(-1)).toBe("0%");
  });
});

describe("heatColour", () => {
  it("returns the sunken colour for an empty cell", () => {
    expect(heatColour(0)).toBe("var(--surface-sunken)");
  });

  it("increases the opacity with the intensity", () => {
    expect(heatColour(1)).not.toBe(heatColour(0.2));
  });
});

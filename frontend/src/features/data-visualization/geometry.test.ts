/** Tests for pure chart maths used by the visualisation UI. */

import { describe, expect, it } from "vitest";
import {
  aggregatePoints,
  axisTicks,
  colorAtIndex,
  niceStep,
  paletteSequence,
  parseSeries,
  radarPolygonPath,
  sankeyCurve,
  sparklineAreaPath,
  sparklineCoordinates,
  sparklinePath,
} from "./geometry";
import { testPalette } from "./fixtures";

describe("sparkline SVG math", () => {
  it("builds an exact polyline path from raw values", () => {
    expect(sparklinePath([0, 5, 10], 10, 10, 0)).toBe(
      "M 0.00 10.00 L 5.00 5.00 L 10.00 0.00",
    );
  });

  it("centres constant series and tolerates empty input", () => {
    expect(sparklinePath([7, 7], 20, 10, 0)).toBe("M 0.00 5.00 L 20.00 5.00");
    expect(sparklinePath([])).toBe("");
    expect(sparklineCoordinates([], 10, 10, 0)).toEqual([]);
  });

  it("closes the area path at the chart baseline", () => {
    const area = sparklineAreaPath([0, 10], 10, 10, 0);
    expect(area.startsWith("M 0.00 10.00 L 10.00 0.00")).toBe(true);
    expect(area.endsWith("L 10.00 10.00 L 0.00 10.00 Z")).toBe(true);
  });
});

describe("axis and palette helpers", () => {
  it("derives readable ticks from a data set", () => {
    expect(niceStep(2.5)).toBe(5);
    expect(axisTicks([1, 9], 5).map((tick) => tick.value)).toEqual([
      0, 2, 4, 6, 8, 10,
    ]);
    expect(axisTicks([])[1].position).toBe(0.5);
  });

  it("selects theme aware palette colours and cycles safely", () => {
    expect(paletteSequence(undefined, "light")).toHaveLength(6);
    expect(paletteSequence(testPalette, "dark")).toEqual(
      testPalette.dark_colors,
    );
    expect(colorAtIndex(0, ["a", "b"])).toBe("a");
    expect(colorAtIndex(5, ["a", "b"])).toBe("b");
    expect(colorAtIndex(0, [])).toBe("#4f46e5");
  });
});

describe("series parsing and aggregation", () => {
  it("parses bare points, named series and object wrappers", () => {
    expect(parseSeries('[{"label":"a","value":2}]')[0].points[0]).toMatchObject(
      {
        label: "a",
        value: 2,
      },
    );
    const parsed = parseSeries(
      '{"series":[{"name":"Alpha","points":[{"label":"x","value":3,"category":"web"}]}]}',
    );
    expect(parsed[0].name).toBe("Alpha");
    expect(parsed[0].points[0].category).toBe("web");
    expect(parseSeries("not json")).toEqual([]);
  });

  it("aggregates points by category with each reduction", () => {
    const points = [
      { label: "a", value: 2, category: "web" },
      { label: "b", value: 4, category: "web" },
      { label: "c", value: 9, category: "crypto" },
    ];
    const sums = aggregatePoints(points, "sum");
    expect(sums.map((row) => [row.category, row.value])).toEqual([
      ["crypto", 9],
      ["web", 6],
    ]);
    expect(aggregatePoints(points, "avg")[1].value).toBe(3);
    expect(aggregatePoints(points, "max")[0].value).toBe(9);
    expect(aggregatePoints(points, "min")[1].value).toBe(2);
    expect(aggregatePoints(points, "count")[0].count).toBe(2);
  });
});

describe("advanced SVG path helpers", () => {
  it("builds closed radar polygons", () => {
    expect(radarPolygonPath([1, 0.5, 0], 10)).toMatch(/^M .* Z$/);
    expect(radarPolygonPath([])).toBe("");
  });

  it("builds cubic Sankey curves with stable control points", () => {
    expect(sankeyCurve(10, 20, 110, 80)).toBe(
      "M 10.00 20.00 C 55.00 20.00, 65.00 80.00, 110.00 80.00",
    );
  });
});

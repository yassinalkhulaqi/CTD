/** Tests for the typed visualisation API adapter. */

import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

function buildQuery(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

vi.mock("../../api/client", () => ({
  buildQuery,
  get: mocks.get,
  post: mocks.post,
  put: mocks.put,
}));

import { visualizationsApi } from "./api";

describe("visualizationsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists and creates chart specifications", async () => {
    mocks.get.mockResolvedValue([]);
    mocks.post.mockResolvedValue({ id: "chart-1" });
    expect(
      await visualizationsApi.list({
        teamId: "team-1",
        chartType: "bar",
        limit: 10,
      }),
    ).toEqual([]);
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations?team_id=team-1&chart_type=bar&limit=10",
      undefined,
    );
    const payload = { title: "Chart", chart_type: "bar" as const };
    expect(await visualizationsApi.create(payload)).toEqual({ id: "chart-1" });
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/visualizations",
      payload,
      undefined,
    );
  });

  it("reads the palette catalogue with a static path", async () => {
    mocks.get.mockResolvedValue([{ id: "aurora" }]);
    expect(await visualizationsApi.palettes()).toEqual([{ id: "aurora" }]);
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations/palettes",
      undefined,
    );
  });

  it("reads, updates and encodes chart identifiers", async () => {
    mocks.get.mockResolvedValue({ id: "chart/1" });
    mocks.put.mockResolvedValue({ id: "chart/1", title: "Updated" });
    await visualizationsApi.get("chart/1");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations/chart%2F1",
      undefined,
    );
    await visualizationsApi.update("chart/1", { title: "Updated" });
    expect(mocks.put).toHaveBeenCalledWith(
      "/api/visualizations/chart%2F1",
      { title: "Updated" },
      undefined,
    );
  });

  it("ingests observations and reads stored data", async () => {
    mocks.post.mockResolvedValue([{ label: "Mon", value: 4 }]);
    mocks.get.mockResolvedValue([{ label: "Mon", value: 4 }]);
    const payload = {
      points: [{ label: "Mon", value: 4, category: "web" }],
      replace: true,
    };
    await visualizationsApi.ingest("chart-1", payload);
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/visualizations/chart-1/data",
      payload,
      undefined,
    );
    await visualizationsApi.data("chart-1");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations/chart-1/data",
      undefined,
    );
  });

  it("serialises geometry and aggregate query parameters", async () => {
    mocks.get.mockResolvedValue({ chart_id: "chart-1" });
    await visualizationsApi.geometry("chart-1", {
      theme: "dark",
      scale: "log",
      tick_count: 4,
    });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations/chart-1/geometry?theme=dark&scale=log&tick_count=4",
      undefined,
    );
    await visualizationsApi.aggregate("chart-1", {
      operation: "sum",
      direction: "desc",
    });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/visualizations/chart-1/aggregate?operation=sum&direction=desc",
      undefined,
    );
  });
});

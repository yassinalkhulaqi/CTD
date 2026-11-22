import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  get: mocks.get,
  post: mocks.post,
  put: mocks.put,
}));

import { scoreboardApi } from "./api";

describe("scoreboard API adapter", () => {
  beforeEach(() => {
    mocks.get.mockReset();
    mocks.post.mockReset();
    mocks.put.mockReset();
  });

  it("loads teams and the live ranking", async () => {
    mocks.get.mockResolvedValueOnce([]).mockResolvedValueOnce({ entries: [] });
    await scoreboardApi.getTeams();
    await scoreboardApi.getRanking();
    expect(mocks.get).toHaveBeenNthCalledWith(1, "/api/teams", {});
    expect(mocks.get).toHaveBeenNthCalledWith(2, "/api/scoreboard/ranking", {});
  });

  it("reads and writes team scoring rules", async () => {
    mocks.get.mockResolvedValue({ id: "rule-1" });
    mocks.put.mockResolvedValue({ id: "rule-1" });
    const signal = new AbortController().signal;
    await scoreboardApi.getRule("team/1", { signal });
    await scoreboardApi.putRule("team/1", {
      name: "Aggressive",
      base_points: 200,
      difficulty_multiplier: 2,
      first_blood_bonus: 75,
      hint_penalty: 5,
      decay_factor: 0.8,
      decay_enabled: false,
    });
    expect(mocks.get).toHaveBeenCalledWith("/api/scoreboard/rules/team%2F1", {
      signal,
    });
    expect(mocks.put).toHaveBeenCalledWith(
      "/api/scoreboard/rules/team%2F1",
      expect.objectContaining({ name: "Aggressive", base_points: 200 }),
      {},
    );
  });

  it("posts snapshots and reads breakdowns and history", async () => {
    mocks.post.mockResolvedValue({ id: "snap-1" });
    mocks.get.mockResolvedValue([]);
    await scoreboardApi.createSnapshot("team-1");
    await scoreboardApi.getBreakdown("team-1");
    await scoreboardApi.getSnapshots("team-1", 10);
    expect(mocks.post).toHaveBeenCalledWith("/api/scoreboard/snapshot/team-1");
    expect(mocks.get).toHaveBeenNthCalledWith(
      1,
      "/api/scoreboard/teams/team-1/breakdown",
      {},
    );
    expect(mocks.get).toHaveBeenNthCalledWith(
      2,
      "/api/scoreboard/snapshots/team-1?limit=10",
      {},
    );
  });
});

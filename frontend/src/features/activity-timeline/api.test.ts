import { beforeEach, describe, expect, it, vi } from "vitest";

vi.setConfig({ testTimeout: 60_000 });

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
}));

vi.mock("../../api/client", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return { ...actual, get: mocks.get, post: mocks.post, del: mocks.del };
});

import { timelineApi } from "./api";

describe("timelineApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists events with repeated and scalar filters", async () => {
    mocks.get.mockResolvedValue({ total: 0 });
    const result = await timelineApi.listEvents({
      teamId: "team-1",
      kinds: ["solve", "note"],
      actors: ["member-1"],
      importance: ["high"],
      limit: 10,
    });
    expect(result).toEqual({ total: 0 });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/timeline?team_id=team-1&limit=10&kinds=solve&kinds=note&actors=member-1&importance=high",
      undefined,
    );

    mocks.get.mockResolvedValue({ total: 1 });
    await timelineApi.listEvents();
    expect(mocks.get).toHaveBeenLastCalledWith("/api/timeline", undefined);
  });

  it("creates, reads and deletes events", async () => {
    const payload = {
      team_id: "team-1",
      kind: "solve",
      actor_id: "member-1",
      actor_name: "Ada Lovelace",
      summary: "Solved RSA",
    };
    mocks.post.mockResolvedValue({ id: "evt-1" });
    mocks.del.mockResolvedValue({ id: "evt/1", deleted: true });

    expect(await timelineApi.createEvent(payload)).toEqual({ id: "evt-1" });
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/timeline",
      payload,
      undefined,
    );

    expect(await timelineApi.deleteEvent("evt/1")).toEqual({
      id: "evt/1",
      deleted: true,
    });
    expect(mocks.del).toHaveBeenCalledWith("/api/timeline/evt%2F1", undefined);
  });

  it("loads groups, stats, actors, kinds and prune results", async () => {
    mocks.get.mockResolvedValue([]);
    await timelineApi.getGroups({ kinds: ["solve"], teamId: "team-1" });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/timeline/groups?team_id=team-1&kinds=solve",
      undefined,
    );

    await timelineApi.getStats({ importance: ["critical"] });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/timeline/stats?importance=critical",
      undefined,
    );

    await timelineApi.getActors("team-1");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/timeline/actors?team_id=team-1",
      undefined,
    );

    await timelineApi.getKinds();
    expect(mocks.get).toHaveBeenCalledWith("/api/timeline/kinds", undefined);

    mocks.post.mockResolvedValue({ deleted: 2 });
    await timelineApi.prune(30);
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/timeline/prune?max_age_days=30",
      undefined,
      undefined,
    );
  });
});

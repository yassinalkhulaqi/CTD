import { beforeEach, describe, expect, it, vi } from "vitest";

const { getMock, postMock, buildQueryMock } = vi.hoisted(() => ({
  getMock: vi.fn<(path: string, options?: unknown) => Promise<{ ok: boolean }>>(
    () => Promise.resolve({ ok: true }),
  ),
  postMock: vi.fn<
    (path: string, payload?: unknown) => Promise<{ ok: boolean }>
  >(() => Promise.resolve({ ok: true })),
  buildQueryMock: vi.fn<(params: Record<string, unknown>) => string>(
    (params) => {
      const entries = Object.entries(params).filter(
        ([, value]) => value !== undefined,
      );
      return entries.length
        ? `?${new URLSearchParams(
            entries.map(([key, value]) => [key, String(value)]),
          ).toString()}`
        : "";
    },
  ),
}));

vi.mock("../../api/client", () => ({
  buildQuery: (params: Record<string, unknown>) => buildQueryMock(params),
  get: (path: string, options?: unknown) => getMock(path, options),
  post: (path: string, payload?: unknown) => postMock(path, payload),
}));

import { ACHIEVEMENTS_PATH, achievementApi } from "./api";

describe("achievement API adapter", () => {
  beforeEach(() => {
    getMock.mockClear();
    postMock.mockClear();
    buildQueryMock.mockClear();
  });

  it("uses the shared achievement prefix", () => {
    expect(ACHIEVEMENTS_PATH).toBe("/api/achievements");
  });

  it("builds filtered catalogue URLs", async () => {
    await achievementApi.listBadges({
      member_id: "member-1",
      tier: "gold",
    });
    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock.mock.calls[0][0]).toContain("/api/achievements/badges?");
    expect(getMock.mock.calls[0][0]).toContain("member_id=member-1");
    expect(getMock.mock.calls[0][0]).toContain("tier=gold");
  });

  it("encodes identifiers in detail paths", async () => {
    await achievementApi.getBadge("gold/one", "member-1");
    expect(getMock.mock.calls[0][0]).toContain(
      "/api/achievements/badges/gold%2Fone",
    );
  });

  it("posts evaluation payloads", async () => {
    await achievementApi.evaluateMember("member-1", { solves: 4 });
    expect(postMock).toHaveBeenCalledWith("/api/achievements/evaluate", {
      member_id: "member-1",
      metrics: { solves: 4 },
    });
  });

  it("posts manual awards and batch evaluation", async () => {
    await achievementApi.awardBadge("member-1", "badge-2", { source: "ui" });
    expect(postMock).toHaveBeenCalledWith(
      "/api/achievements/members/member-1/awards/badge-2",
      { evidence: { source: "ui" } },
    );
    await achievementApi.evaluateBatch([
      { member_id: "member-1", metrics: { solves: 1 } },
    ]);
    expect(postMock).toHaveBeenLastCalledWith(
      "/api/achievements/evaluate/batch",
      { submissions: [{ member_id: "member-1", metrics: { solves: 1 } }] },
    );
  });
});

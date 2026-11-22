import { beforeEach, describe, expect, it, vi } from "vitest";

const getMock = vi.hoisted(() => vi.fn());
const postMock = vi.hoisted(() => vi.fn());

vi.mock("../../api/client", () => ({
  buildQuery: (
    params: Record<string, string | number | boolean | null | undefined>,
  ): string => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined || value === "") continue;
      query.set(key, String(value));
    }
    const encoded = query.toString();
    return encoded ? `?${encoded}` : "";
  },
  get: (path: string, options: unknown) => getMock(path, options),
  post: (path: string, body: unknown, options: unknown) =>
    postMock(path, body, options),
}));

import { adminApi } from "./api";
import { DEFAULT_ACTION_FILTER, DEFAULT_CASE_FILTER } from "./types";

describe("admin API adapter", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    getMock.mockResolvedValue({ items: [], total: 0 });
    postMock.mockResolvedValue({});
  });

  it("maps case filters onto the documented query contract", async () => {
    await adminApi.listCases({
      ...DEFAULT_CASE_FILTER,
      status: "open",
      reportType: "cheating",
      overdueOnly: true,
      limit: 25,
    });

    expect(getMock).toHaveBeenCalledTimes(1);
    const path = getMock.mock.calls[0][0] as string;
    const query = new URLSearchParams(path.split("?")[1]);
    expect(path.startsWith("/api/admin/cases?")).toBe(true);
    expect(query.get("status")).toBe("open");
    expect(query.get("report_type")).toBe("cheating");
    expect(query.get("overdue")).toBe("true");
    expect(query.get("limit")).toBe("25");
    expect(query.has("priority")).toBe(false);
  });

  it("maps audit filters onto the documented query contract", async () => {
    await adminApi.listActions({
      ...DEFAULT_ACTION_FILTER,
      action: "account_suspended",
      actorId: "moderator-1",
    });

    const path = getMock.mock.calls[0][0] as string;
    const query = new URLSearchParams(path.split("?")[1]);
    expect(query.get("action")).toBe("account_suspended");
    expect(query.get("actor_id")).toBe("moderator-1");
    expect(query.has("target_type")).toBe(false);
  });

  it("posts lifecycle and account control payloads to the right routes", async () => {
    await adminApi.assignCase("case-1", "moderator-1");
    await adminApi.resolveCase("case-1", "handled");
    await adminApi.setAccountStatus({
      user_id: "user-1",
      status: "suspended",
      reason: "abuse",
      flags: ["reviewed"],
    });

    expect(postMock).toHaveBeenNthCalledWith(
      1,
      "/api/admin/cases/case-1/assign",
      { assignee_id: "moderator-1" },
      expect.objectContaining({ signal: undefined }),
    );
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      "/api/admin/cases/case-1/resolve",
      { resolution: "handled" },
      expect.anything(),
    );
    expect(postMock).toHaveBeenNthCalledWith(
      3,
      "/api/admin/account-controls",
      {
        user_id: "user-1",
        status: "suspended",
        reason: "abuse",
        flags: ["reviewed"],
      },
      expect.anything(),
    );
  });
});

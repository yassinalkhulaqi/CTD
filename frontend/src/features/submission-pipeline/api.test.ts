import { beforeEach, describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../../api/client", () => ({
  get: (...args: unknown[]) => getMock(...args),
  post: (...args: unknown[]) => postMock(...args),
  buildQuery: (params?: Record<string, string | number | undefined>) => {
    if (!params) return "";
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === "") continue;
      search.set(key, String(value));
    }
    const encoded = search.toString();
    return encoded ? `?${encoded}` : "";
  },
}));

import { submissionsApi } from "./api";

describe("submissions API adapter", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    getMock.mockResolvedValue([]);
    postMock.mockResolvedValue({});
  });

  it("maps filters to the list query", async () => {
    await submissionsApi.list({
      status: "rejected",
      challenge_id: "challenge-1",
      member_id: "member-1",
    });
    const [path] = getMock.mock.calls[0] as [string];
    expect(path).toContain("/api/submissions?");
    expect(path).toContain("status=rejected");
    expect(path).toContain("challenge_id=challenge-1");
    expect(path).toContain("member_id=member-1");
    expect(path).toContain("limit=200");
  });

  it("omits the status parameter for the all filter", async () => {
    await submissionsApi.list({
      status: "all",
      challenge_id: "",
      member_id: "",
    });
    const [path] = getMock.mock.calls[0] as [string];
    expect(path).toBe("/api/submissions?limit=200");
  });

  it("posts a validated submission draft", async () => {
    const draft = { challenge_id: "c1", member_id: "m1", flag: "flag{abc}" };
    await submissionsApi.submit(draft);
    expect(postMock).toHaveBeenCalledWith("/api/submissions", draft, undefined);
  });

  it("posts a retry with an optional replacement flag", async () => {
    await submissionsApi.retry("sub-1");
    await submissionsApi.retry("sub-2", "flag{fixed_value}");
    expect(postMock).toHaveBeenNthCalledWith(
      1,
      "/api/submissions/sub-1/retry",
      {},
      undefined,
    );
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      "/api/submissions/sub-2/retry",
      { flag: "flag{fixed_value}" },
      undefined,
    );
  });

  it("posts the queue processing limit", async () => {
    await submissionsApi.process(25);
    expect(postMock).toHaveBeenCalledWith(
      "/api/submissions/process",
      { limit: 25 },
      undefined,
    );
  });

  it("reads stats, rules and reference data from the right endpoints", async () => {
    await submissionsApi.stats();
    await submissionsApi.rules();
    await submissionsApi.challenges();
    await submissionsApi.members();
    expect(getMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/submissions/stats",
      "/api/submissions/rules",
      "/api/challenges",
      "/api/members",
    ]);
  });

  it("creates a validation rule and reads a single submission", async () => {
    await submissionsApi.createRule({
      name: "Custom",
      pattern: "^flag\\{.*\\}$",
      description: "Custom rule",
      enabled: true,
      priority: 10,
      kind: "format",
    });
    await submissionsApi.get("sub-1");
    const [rulePath, ruleBody] = postMock.mock.calls[0] as [string, unknown];
    expect(rulePath).toBe("/api/submissions/rules");
    expect(ruleBody).toMatchObject({ name: "Custom" });
    expect(getMock).toHaveBeenCalledWith("/api/submissions/sub-1", undefined);
  });
});

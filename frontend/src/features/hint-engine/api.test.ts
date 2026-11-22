import { afterEach, describe, expect, it, vi } from "vitest";
import { hintsApi } from "./api";

const originalFetch = globalThis.fetch;

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  const spy = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(String(input), init)),
  );
  globalThis.fetch = spy as unknown as typeof fetch;
  return spy;
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("hintsApi", () => {
  it("encodes challenge views and their query parameters", async () => {
    const spy = mockFetch(() => json({ hints: [], challenge_id: "c/1" }));
    await hintsApi.challengeView("c/1", "team 2", "member/3");
    expect(spy.mock.calls[0][0]).toBe(
      "/api/hints/challenges/c%2F1?team_id=team+2&member_id=member%2F3",
    );
  });

  it("posts an unlock request with the team and member identifiers", async () => {
    const spy = mockFetch(() => json({ id: "unlock-1", cost_paid: 25 }));
    const result = await hintsApi.unlock("hint 1", "member-2", "team-3");
    expect(result.cost_paid).toBe(25);
    expect(spy.mock.calls[0][0]).toBe("/api/hints/hint%201/unlock");
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      member_id: "member-2",
      team_id: "team-3",
    });
  });

  it("serialises list filters and reset settings", async () => {
    const spy = mockFetch((url) =>
      json(url.includes("reset") ? { total: 900 } : []),
    );
    await hintsApi.list({ challengeId: "challenge-1", teamId: "team-1" });
    expect(spy.mock.calls[0][0]).toBe(
      "/api/hints?challenge_id=challenge-1&team_id=team-1",
    );
    await hintsApi.resetBudget("team-1", {
      total: 900,
      reset_after_seconds: 60,
    });
    expect(spy.mock.calls[1][0]).toBe("/api/hints/budget/team-1/reset");
    const init = spy.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({
      total: 900,
      reset_after_seconds: 60,
    });
  });

  it("uses the expected paths for catalogue and ledger resources", async () => {
    const spy = mockFetch(() => json([]));
    await hintsApi.ledger("team-1");
    await hintsApi.teams();
    await hintsApi.challenges("team-1");
    await hintsApi.members("team-1");
    expect(spy.mock.calls.map((call) => call[0])).toEqual([
      "/api/hints/ledger/team-1",
      "/api/teams",
      "/api/challenges?team_id=team-1",
      "/api/members?team_id=team-1",
    ]);
  });

  it("uses patch and delete verbs for catalogue edits", async () => {
    const spy = mockFetch(() => new Response(null, { status: 204 }));
    await hintsApi.update("hint-1", { title: "New title" });
    await hintsApi.remove("hint-2");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("PATCH");
    expect((spy.mock.calls[1][1] as RequestInit).method).toBe("DELETE");
  });
});

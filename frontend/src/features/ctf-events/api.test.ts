/** API adapter tests for the event endpoints. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { eventsApi } from "./api";

const originalFetch = globalThis.fetch;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
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

function bodyOf(init: RequestInit | undefined): Record<string, unknown> {
  return JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
}

describe("eventsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("lists events with encoded filters", async () => {
    const spy = mockFetch(() =>
      jsonResponse({ events: [], total: 0, window: "live" }),
    );
    const result = await eventsApi.list({
      window: "live",
      search: "finals",
      limit: 10,
    });
    expect(result.total).toBe(0);
    expect(spy.mock.calls[0][0]).toContain(
      "/api/events?window=live&search=finals&limit=10",
    );
  });

  it("fetches a single event and its stats", async () => {
    const spy = mockFetch((url) =>
      url.endsWith("/stats")
        ? jsonResponse({ event_id: "e1", capacity: 4, confirmed: 2 })
        : jsonResponse({ id: "e1", name: "Finals" }),
    );
    const event = await eventsApi.get("e 1");
    const stats = await eventsApi.stats("e1");
    expect(event.name).toBe("Finals");
    expect(stats.confirmed).toBe(2);
    expect(spy.mock.calls[0][0]).toContain(encodeURIComponent("e 1"));
  });

  it("posts a registration with the team identifier", async () => {
    const spy = mockFetch(() =>
      jsonResponse(
        { id: "reg-1", status: "confirmed", is_waitlisted: false },
        201,
      ),
    );
    const registration = await eventsApi.register("event-1", "team-1");
    expect(registration.status).toBe("confirmed");
    expect(spy.mock.calls[0][0]).toBe("/api/events/event-1/register");
    expect(bodyOf(spy.mock.calls[0][1])).toEqual({ team_id: "team-1" });
    expect(spy.mock.calls[0][1]?.method).toBe("POST");
  });

  it("cancels a registration", async () => {
    const spy = mockFetch(() =>
      jsonResponse({ event_id: "e1", team_id: "t1", status: "cancelled" }),
    );
    const result = await eventsApi.cancel("e1", "t1");
    expect(result.status).toBe("cancelled");
    expect(bodyOf(spy.mock.calls[0][1])).toEqual({ team_id: "t1" });
  });

  it("creates and toggles checklist items", async () => {
    const spy = mockFetch((url) =>
      url.endsWith("/toggle")
        ? jsonResponse({ id: "task-1", done: true })
        : jsonResponse({ id: "task-1", title: "Pack gear" }, 201),
    );
    const created = await eventsApi.addTask("e1", "Pack gear");
    const toggled = await eventsApi.toggleTask("e1", created.id);
    expect(created.title).toBe("Pack gear");
    expect(toggled.done).toBe(true);
    expect(bodyOf(spy.mock.calls[0][1])).toEqual({
      title: "Pack gear",
      due_at: null,
    });
    expect(spy.mock.calls[1][0]).toBe("/api/events/e1/tasks/task-1/toggle");
  });

  it("loads teams and overlaps", async () => {
    const spy = mockFetch((url) =>
      url.includes("/overlaps")
        ? jsonResponse({ team_id: "t1", overlaps: [] })
        : jsonResponse([{ id: "t1", name: "Alpha" }]),
    );
    const teams = await eventsApi.teams();
    const overlaps = await eventsApi.overlaps("t1");
    expect(teams[0].name).toBe("Alpha");
    expect(overlaps.overlaps).toEqual([]);
    expect(spy.mock.calls[1][0]).toBe("/api/events/overlaps?team_id=t1");
  });

  it("deletes an event", async () => {
    const spy = mockFetch(() => new Response(null, { status: 204 }));
    await eventsApi.remove("e1");
    expect(spy.mock.calls[0][1]?.method).toBe("DELETE");
  });
});

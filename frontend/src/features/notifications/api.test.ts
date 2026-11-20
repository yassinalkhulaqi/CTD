/** API adapter tests for the notification centre. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configureAuth } from "../../api/client";
import {
  buildDigest,
  createNotification,
  getDigestPreview,
  getStats,
  listNotifications,
  listPreferences,
  markAllRead,
  markNotificationRead,
  pruneNotifications,
  sendDigest,
  upsertPreference,
} from "./api";

const originalFetch = globalThis.fetch;

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  const spy = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(String(input), init)),
  );
  globalThis.fetch = spy as unknown as typeof fetch;
  return spy;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("notification API adapter", () => {
  beforeEach(() => {
    configureAuth(() => null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("builds a filtered listing URL", async () => {
    const spy = mockFetch(() =>
      jsonResponse({ items: [], total: 0, unread: 0, limit: 100, offset: 0 }),
    );
    const page = await listNotifications({
      recipientId: "member-1",
      kind: "solve",
      unreadOnly: true,
      limit: 10,
    });
    expect(page.total).toBe(0);
    expect(spy.mock.calls[0][0]).toBe(
      "/api/notifications?recipient_id=member-1&kind=solve&unread_only=true&limit=10",
    );
  });

  it("posts a notification payload", async () => {
    const spy = mockFetch(() => jsonResponse({ delivered: true }, 201));
    await createNotification({
      recipient_id: "member-1",
      channel: "email",
      kind: "team",
      title: "Hello",
      body: "World",
    });
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toMatchObject({
      recipient_id: "member-1",
    });
  });

  it("acknowledges one and all notifications", async () => {
    const spy = mockFetch((url) =>
      jsonResponse(url.includes("read-all") ? { modified: 2 } : { id: "n1" }),
    );
    await markNotificationRead("n 1");
    await markAllRead("member-1");
    expect(spy.mock.calls[0][0]).toBe("/api/notifications/n%201/read");
    expect(spy.mock.calls[1][1]?.method).toBe("POST");
    expect(spy.mock.calls[1][0]).toBe("/api/notifications/read-all");
  });

  it("reads and writes preferences", async () => {
    const spy = mockFetch(() => jsonResponse({ preferences: [] }));
    await listPreferences("member-1");
    expect(spy.mock.calls[0][0]).toBe(
      "/api/notifications/preferences?recipient_id=member-1",
    );
    await upsertPreference({
      recipient_id: "member-1",
      channel: "email",
      kind: "security",
      enabled: false,
      quiet_start_hour: 22,
      quiet_end_hour: 6,
    });
    expect(spy.mock.calls[1][1]?.method).toBe("PUT");
  });

  it("previews, builds and sends digests", async () => {
    const spy = mockFetch(() => jsonResponse({ total: 1, groups: [] }));
    await getDigestPreview("member-1", "weekly");
    await buildDigest("member-1", "daily");
    await sendDigest("dgt-1");
    expect(spy.mock.calls[0][0]).toBe(
      "/api/notifications/digest?recipient_id=member-1&period=weekly",
    );
    expect(spy.mock.calls[1][1]?.method).toBe("POST");
    expect(spy.mock.calls[2][0]).toBe("/api/notifications/digest/send");
  });

  it("reads stats and prunes old notifications", async () => {
    const spy = mockFetch(() => jsonResponse({ total: 3, unread: 1 }));
    await getStats("member-1");
    await pruneNotifications(14, false);
    expect(spy.mock.calls[0][0]).toBe(
      "/api/notifications/stats?recipient_id=member-1",
    );
    expect(JSON.parse(String(spy.mock.calls[1][1]?.body))).toEqual({
      max_age_days: 14,
      keep_unread: false,
    });
  });
});

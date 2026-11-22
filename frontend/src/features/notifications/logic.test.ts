/** Pure notification logic tests. */

import { describe, expect, it } from "vitest";
import {
  digestHeadline,
  filterNotifications,
  isPreferenceEnabled,
  isWithinQuietHours,
  makeToast,
  normaliseHour,
  setQuietHours,
  shouldAutoDismiss,
  sortNotifications,
  togglePreference,
  trimToasts,
} from "./logic";
import type { Notification, Preference, Severity } from "./types";

function notification(
  id: string,
  overrides: Partial<Notification> = {},
): Notification {
  return {
    id,
    recipient_id: "member-1",
    channel: "in_app",
    kind: "system",
    title: `Title ${id}`,
    body: `Body ${id}`,
    severity: "info",
    read_at: null,
    created_at: "2026-01-01T10:00:00Z",
    action_url: "",
    is_read: false,
    is_unread: true,
    severity_rank: 0,
    label: "system · info",
    age_seconds: 10,
    ...overrides,
  };
}

function preference(overrides: Partial<Preference> = {}): Preference {
  return {
    recipient_id: "member-1",
    channel: "in_app",
    kind: "solve",
    enabled: true,
    quiet_start_hour: 0,
    quiet_end_hour: 0,
    quiet_hours: "No quiet hours",
    ...overrides,
  };
}

describe("hour helpers", () => {
  it("normalises hours into the 0–23 range", () => {
    expect(normaliseHour(-5)).toBe(0);
    expect(normaliseHour(30)).toBe(23);
    expect(normaliseHour(7.8)).toBe(7);
    expect(normaliseHour(Number.NaN)).toBe(0);
  });

  it("detects plain quiet windows", () => {
    expect(isWithinQuietHours(9, 17, 10)).toBe(true);
    expect(isWithinQuietHours(9, 17, 17)).toBe(false);
    expect(isWithinQuietHours(9, 17, 8)).toBe(false);
  });

  it("detects overnight quiet windows", () => {
    expect(isWithinQuietHours(22, 6, 23)).toBe(true);
    expect(isWithinQuietHours(22, 6, 3)).toBe(true);
    expect(isWithinQuietHours(22, 6, 12)).toBe(false);
    expect(isWithinQuietHours(0, 0, 12)).toBe(false);
  });
});

describe("preference logic", () => {
  it("prefers exact rows over wildcards and defaults", () => {
    const rows = [
      preference({ channel: "email", kind: "*", enabled: false }),
      preference({ channel: "email", kind: "security", enabled: true }),
    ];
    expect(isPreferenceEnabled(rows, "email", "security")).toBe(true);
    expect(isPreferenceEnabled(rows, "email", "solve")).toBe(false);
    expect(isPreferenceEnabled(rows, "webhook", "solve")).toBe(true);
  });

  it("toggles a preference and inserts a missing row", () => {
    const rows = [preference()];
    const updated = togglePreference(rows, "in_app", "solve", false);
    expect(updated).toHaveLength(1);
    expect(updated[0].enabled).toBe(false);
    const inserted = togglePreference(rows, "email", "team", false);
    expect(inserted).toHaveLength(2);
    expect(inserted[1]).toMatchObject({
      channel: "email",
      kind: "team",
      enabled: false,
      recipient_id: "member-1",
    });
  });

  it("normalises quiet hours changes", () => {
    const rows = [preference()];
    const updated = setQuietHours(rows, "in_app", "solve", -4, 99);
    expect(updated[0].quiet_start_hour).toBe(0);
    expect(updated[0].quiet_end_hour).toBe(23);
  });
});

describe("notification list logic", () => {
  const items = [
    notification("a", { severity: "info" as Severity }),
    notification("b", { severity: "critical" as Severity, kind: "security" }),
    notification("c", {
      severity: "warning" as Severity,
      is_unread: false,
      is_read: true,
    }),
  ];

  it("sorts by severity before recency", () => {
    expect(sortNotifications(items).map((item) => item.id)).toEqual([
      "b",
      "c",
      "a",
    ]);
  });

  it("filters by kind, severity, unread state and search", () => {
    expect(
      filterNotifications(items, {
        kind: "security",
        severity: "all",
        unreadOnly: false,
        search: "",
      }).map((item) => item.id),
    ).toEqual(["b"]);
    expect(
      filterNotifications(items, {
        kind: "all",
        severity: "warning",
        unreadOnly: false,
        search: "",
      }).map((item) => item.id),
    ).toEqual(["c"]);
    expect(
      filterNotifications(items, {
        kind: "all",
        severity: "all",
        unreadOnly: true,
        search: "body c",
      }),
    ).toEqual([]);
  });
});

describe("toast helpers", () => {
  it("creates bounded toasts with auto-dismiss", () => {
    const toast = makeToast(notification("t1"), 1000, 0);
    expect(toast).toMatchObject({ id: "toast-t1", tone: "info", ttl: 1000 });
    expect(shouldAutoDismiss(toast, 999)).toBe(false);
    expect(shouldAutoDismiss(toast, 1000)).toBe(true);
    expect(shouldAutoDismiss({ ...toast, ttl: 0 }, 5000)).toBe(false);
    const queue = trimToasts(
      [toast, makeToast(notification("t2")), makeToast(notification("t3"))],
      2,
    );
    expect(queue.map((item) => item.id)).toEqual(["toast-t2", "toast-t3"]);
    expect(trimToasts([toast], 0)).toEqual([]);
  });
});

describe("digest helpers", () => {
  it("summarises empty and populated previews", () => {
    expect(digestHeadline(null)).toBe("No notifications in this period");
    expect(
      digestHeadline({
        recipient_id: "member-1",
        period: "daily",
        total: 1,
        groups: [],
        entries: [],
        markdown: "",
        generated_at: "2026-01-01T00:00:00Z",
      }),
    ).toContain("1 notification");
  });
});

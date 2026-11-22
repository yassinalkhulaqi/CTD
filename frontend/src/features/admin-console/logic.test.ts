import { describe, expect, it } from "vitest";
import {
  canSuspend,
  filterActions,
  filterCases,
  formatSla,
  healthScore,
  healthStateFor,
  summarizeAccounts,
} from "./logic";
import {
  DEFAULT_ACTION_FILTER,
  DEFAULT_CASE_FILTER,
  type AccountControl,
  type AdminAction,
  type ModerationCase,
} from "./types";

function makeCase(overrides: Partial<ModerationCase> = {}): ModerationCase {
  return {
    id: "case-1",
    report_type: "cheating",
    target_id: "team-2",
    reporter_id: "team-3",
    status: "open",
    priority: "high",
    assignee_id: null,
    resolution: null,
    created_at: "2026-01-01T00:00:00Z",
    due_at: "2026-01-02T00:00:00Z",
    is_overdue: false,
    is_terminal: false,
    sla_hours: 8,
    ...overrides,
  };
}

function makeAction(overrides: Partial<AdminAction> = {}): AdminAction {
  return {
    id: "action-1",
    actor_id: "moderator-1",
    target_type: "case",
    target_id: "case-1",
    action: "case_resolved",
    reason: "Confirmed reused nonce",
    created_at: "2026-01-01T00:00:00Z",
    summary: "Resolved case-1",
    ...overrides,
  };
}

function makeAccount(overrides: Partial<AccountControl> = {}): AccountControl {
  return {
    user_id: "user-1",
    username: "player",
    role: "participant",
    status: "active",
    flags: [],
    updated_at: "2026-01-01T00:00:00Z",
    is_suspended: false,
    auth_active: true,
    is_consistent: true,
    ...overrides,
  };
}

describe("administration pure logic", () => {
  it("scores health from the weighted metrics", () => {
    expect(
      healthScore({
        database_ok: true,
        api_latency_ms: 0,
        cache_hit_ratio: 1,
        queue_depth: 0,
      }),
    ).toBe(100);
    expect(healthStateFor(92, true)).toBe("healthy");
    expect(healthStateFor(72, true)).toBe("degraded");
    expect(healthStateFor(92, false)).toBe("critical");
  });

  it("formats remaining and breached SLA windows", () => {
    const now = Date.parse("2026-01-01T00:00:00Z");
    expect(formatSla(makeCase(), now)).toBe("1d 0h left");
    expect(
      formatSla(
        makeCase({ due_at: "2026-01-01T00:00:00Z", is_overdue: true }),
        now + 30_000,
      ),
    ).toBe("overdue 30s");
    expect(formatSla(makeCase({ is_terminal: true }), now)).toBe("closed");
  });

  it("filters and sorts the moderation queue", () => {
    const cases = [
      makeCase(),
      makeCase({ id: "case-2", priority: "critical" }),
      makeCase({ id: "case-3", priority: "low", report_type: "spam" }),
    ];
    const result = filterCases(cases, {
      ...DEFAULT_CASE_FILTER,
      priority: "high",
    });
    expect(result.map((item) => item.id)).toEqual(["case-1"]);
    expect(
      filterCases(cases, {
        ...DEFAULT_CASE_FILTER,
        reportType: "spam",
      }).map((item) => item.id),
    ).toEqual(["case-3"]);
    expect(
      filterCases(cases, {
        ...DEFAULT_CASE_FILTER,
        sort: "priority_desc",
      }).map((item) => item.id),
    ).toEqual(["case-2", "case-1", "case-3"]);
  });

  it("filters the audit trail by actor, target and search", () => {
    const actions = [
      makeAction(),
      makeAction({
        id: "action-2",
        actor_id: "admin-1",
        target_type: "account",
        action: "account_suspended",
        reason: "Abusive account",
      }),
    ];
    expect(
      filterActions(actions, {
        ...DEFAULT_ACTION_FILTER,
        targetType: "account",
      }).map((entry) => entry.id),
    ).toEqual(["action-2"]);
    expect(
      filterActions(actions, { ...DEFAULT_ACTION_FILTER, search: "nonce" }).map(
        (entry) => entry.id,
      ),
    ).toEqual(["action-1"]);
    expect(
      filterActions(actions, { ...DEFAULT_ACTION_FILTER, actorId: "ADMIN" }),
    ).toHaveLength(1);
  });

  it("protects administrators and the operator from suspension", () => {
    expect(canSuspend(makeAccount(), "admin-1")).toBe(true);
    expect(canSuspend(makeAccount({ user_id: "admin-1" }), "admin-1")).toBe(
      false,
    );
    expect(canSuspend(makeAccount({ role: "admin" }), "admin-1")).toBe(false);
  });

  it("summarises account posture", () => {
    expect(
      summarizeAccounts([
        makeAccount(),
        makeAccount({
          user_id: "user-2",
          is_suspended: true,
          status: "suspended",
        }),
        makeAccount({ user_id: "user-3", flags: ["watch"] }),
      ]),
    ).toEqual({ total: 3, active: 2, suspended: 1, flagged: 1 });
  });
});

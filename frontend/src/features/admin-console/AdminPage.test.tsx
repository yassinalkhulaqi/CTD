import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { UseAdminConsoleResult } from "./hooks";
import type {
  AccountControl,
  AdminAction,
  AdminConsoleData,
  AdminStats,
  ModerationCase,
  SystemHealth,
} from "./types";

const mockUseAdminConsole = vi.hoisted(() => vi.fn());

vi.mock("./hooks", () => ({
  useAdminConsole: () => mockUseAdminConsole(),
}));

import { AdminPage } from "./AdminPage";

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

function makeAction(): AdminAction {
  return {
    id: "action-1",
    actor_id: "admin",
    target_type: "case",
    target_id: "case-1",
    action: "case_opened",
    reason: "Reported cheating",
    created_at: "2026-01-01T00:00:00Z",
    summary: "Opened case-1",
  };
}

function makeHealth(): SystemHealth {
  return {
    id: "health-1",
    checked_at: "2026-01-01T00:00:00Z",
    database_ok: true,
    api_latency_ms: 120,
    cache_hit_ratio: 0.92,
    queue_depth: 4,
    score: 94.6,
    state: "healthy",
    bottleneck: "api_latency",
    is_healthy: true,
  };
}

function makeStats(): AdminStats {
  return {
    total_cases: 1,
    open_cases: 1,
    in_review_cases: 0,
    resolved_cases: 0,
    dismissed_cases: 0,
    active_cases: 1,
    overdue_cases: 0,
    critical_cases: 0,
    suspended_accounts: 0,
    actions_24h: 1,
    health_checks: 1,
    latest_score: 94.6,
    database_ok: true,
    resolution_rate: 0,
    attention_score: 1,
    health_state: "healthy",
    priority_counts: { high: 1 },
    report_counts: { cheating: 1 },
  };
}

function makeData(): AdminConsoleData {
  return {
    cases: { items: [makeCase()], total: 1, limit: 50, offset: 0 },
    accounts: { items: [makeAccount()], suspended: 0 },
    actions: { items: [makeAction()], total: 1, limit: 100, offset: 0 },
    health: { items: [makeHealth()], latest: makeHealth() },
    stats: makeStats(),
  };
}

function makeHook(
  overrides: Partial<UseAdminConsoleResult> = {},
): UseAdminConsoleResult {
  return {
    data: makeData(),
    loading: false,
    busy: null,
    error: null,
    refresh: vi.fn().mockResolvedValue(undefined),
    loadCases: vi.fn().mockResolvedValue(undefined),
    updateCase: vi.fn().mockResolvedValue(true),
    openCase: vi.fn().mockResolvedValue(true),
    changeAccountStatus: vi.fn().mockResolvedValue(true),
    recordHealth: vi.fn().mockResolvedValue(true),
    clearError: vi.fn(),
    ...overrides,
  };
}

describe("AdminPage", () => {
  beforeEach(() => {
    mockUseAdminConsole.mockReturnValue(makeHook());
  });

  it("renders every administration surface", () => {
    render(<AdminPage />);

    expect(
      screen.getByRole("heading", { name: "Administration console" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Moderation queue")).toBeInTheDocument();
    expect(screen.getByText("Audit trail")).toBeInTheDocument();
    expect(screen.getByText("System health")).toBeInTheDocument();
    expect(screen.getByText("Account controls")).toBeInTheDocument();
    expect(screen.getByText(/team-2/)).toBeInTheDocument();
  });

  it("assigns the selected case to the operator", async () => {
    const hook = makeHook();
    mockUseAdminConsole.mockReturnValue(hook);
    render(<AdminPage />);

    fireEvent.click(screen.getByRole("button", { name: "Review case case-1" }));
    fireEvent.click(screen.getByRole("button", { name: "Assign to me" }));

    await waitFor(() =>
      expect(hook.updateCase).toHaveBeenCalledWith("case-1", "assign", "admin"),
    );
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Case case-1 assigned",
      ),
    );
  });
});

import { describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { AccountControls } from "./components/AccountControls";
import { CaseDetail } from "./components/CaseDetail";
import { HealthGauge } from "./components/HealthGauge";
import { ModerationQueue } from "./components/ModerationQueue";
import {
  DEFAULT_CASE_FILTER,
  type AccountControl,
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

describe("administration components", () => {
  it("reports moderation filter and case selection interactions", () => {
    const onFilterChange = vi.fn();
    const onSelect = vi.fn();
    const item = makeCase();

    render(
      <ModerationQueue
        cases={[item]}
        total={1}
        filter={{ ...DEFAULT_CASE_FILTER }}
        onFilterChange={onFilterChange}
        onSelect={onSelect}
      />,
    );

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "in_review" },
    });
    expect(onFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({ status: "in_review" }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Review case case-1" }));
    expect(onSelect).toHaveBeenCalledWith(item);
  });

  it("requires a written resolution before closing a case", () => {
    const onResolve = vi.fn();
    const item = makeCase();

    render(
      <CaseDetail
        item={item}
        operatorId="admin-1"
        onAssign={() => undefined}
        onResolve={onResolve}
        onDismiss={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Resolve" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm resolution" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Describe the resolution",
    );
    expect(onResolve).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Resolution"), {
      target: { value: "Ban evasion confirmed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm resolution" }));
    expect(onResolve).toHaveBeenCalledWith(item, "Ban evasion confirmed");
  });

  it("disables suspension for self and administrator accounts", () => {
    const onSetStatus = vi.fn();
    render(
      <AccountControls
        accounts={[
          makeAccount({ user_id: "self", username: "self" }),
          makeAccount({ user_id: "admin-1", username: "root", role: "admin" }),
          makeAccount({ user_id: "user-2", username: "suspect" }),
        ]}
        operatorId="self"
        onSetStatus={onSetStatus}
      />,
    );

    expect(
      within(screen.getByRole("row", { name: /self/ })).getByRole("button", {
        name: "Suspend",
      }),
    ).toBeDisabled();
    expect(
      within(screen.getByRole("row", { name: /root/ })).getByRole("button", {
        name: "Suspend",
      }),
    ).toBeDisabled();
    expect(
      within(screen.getByRole("row", { name: /suspect/ })).getByRole("button", {
        name: "Suspend",
      }),
    ).toBeEnabled();
  });

  it("records a health snapshot with converted metrics", async () => {
    const onRecord = vi.fn().mockResolvedValue(true);
    render(<HealthGauge health={null} onRecord={onRecord} />);

    fireEvent.change(screen.getByLabelText("API latency (ms)"), {
      target: { value: "220" },
    });
    fireEvent.change(screen.getByLabelText("Cache hit ratio (%)"), {
      target: { value: "80" },
    });
    fireEvent.change(screen.getByLabelText("Queue depth"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save health check" }));

    await waitFor(() =>
      expect(onRecord).toHaveBeenCalledWith({
        database_ok: true,
        api_latency_ms: 220,
        cache_hit_ratio: 0.8,
        queue_depth: 3,
      }),
    );
  });
});

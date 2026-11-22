import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PendingMutation, SyncStatus } from "./types";

const controller = vi.hoisted(() => ({
  queue: [] as PendingMutation[],
  status: null as SyncStatus | null,
  loading: false,
  busy: false,
  online: true,
  error: null as string | null,
  refresh: vi.fn(async () => undefined),
  syncNow: vi.fn(async () => null),
  resolve: vi.fn(async () => true),
  clear: vi.fn(async () => true),
  dismissError: vi.fn(),
}));

vi.mock("./hooks", () => ({
  useOfflineSync: () => controller,
  useOnlineStatus: () => controller.online,
}));

import { OfflinePage } from "./OfflinePage";

const pending: PendingMutation = {
  id: "mut-1",
  client_id: "phone",
  entity: "challenge",
  operation: "create",
  payload: { title: "Beta" },
  base_version: 1,
  created_at: "2026-01-01T12:00:00.000Z",
  status: "pending",
  attempts: 0,
  last_error: "",
  resolved_version: null,
  entity_label: "Challenge",
  is_pending: true,
  next_retry_delay: 2,
};

const conflict: PendingMutation = {
  ...pending,
  id: "mut-2",
  entity: "note",
  operation: "update",
  entity_label: "Note",
  status: "conflict",
  attempts: 2,
  last_error: "version conflict",
  base_version: 4,
};

const status: SyncStatus = {
  pending: 1,
  synced: 3,
  conflict: 1,
  total: 5,
  attempts: 4,
  backlog: 2,
  completion_rate: 0.6,
  average_attempts: 1.2,
  health_label: "attention",
  has_conflicts: true,
  oldest_pending: pending.created_at,
  newest_synced: "2026-01-01T11:00:00.000Z",
  stale: false,
  resolution_count: 1,
  latest_snapshot: null,
};

function reset(overrides: Partial<typeof controller> = {}): void {
  controller.queue = [];
  controller.status = null;
  controller.loading = false;
  controller.busy = false;
  controller.online = true;
  controller.error = null;
  controller.refresh.mockClear();
  controller.syncNow.mockClear();
  controller.resolve.mockClear();
  controller.clear.mockClear();
  controller.dismissError.mockClear();
  Object.assign(controller, overrides);
}

beforeEach(() => {
  reset();
});

describe("OfflinePage", () => {
  it("renders the workspace with connectivity, status and queue sections", () => {
    render(<OfflinePage />);
    expect(screen.getByRole("heading", { name: "Offline & Sync" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sync status" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mutation queue" })).toBeInTheDocument();
    expect(screen.getAllByRole("status")[0]).toHaveAttribute(
      "data-connectivity",
      "online",
    );
    expect(screen.getByText("The queue is empty")).toBeInTheDocument();
  });

  it("lists conflicts and opens the resolution dialog", async () => {
    const user = userEvent.setup();
    reset({ queue: [pending, conflict], status });

    render(<OfflinePage />);

    expect(screen.getAllByText(/Note/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Note v4/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Note v4/ }));

    expect(screen.getByRole("dialog", { name: "Resolve version conflict" })).toBeInTheDocument();
    expect(screen.getByText("Offline edit")).toBeInTheDocument();
    expect(screen.getByText("Current server version")).toBeInTheDocument();
    expect(screen.getByText("Resolved payload preview")).toBeInTheDocument();
  });

  it("submits the chosen resolution and closes the dialog", async () => {
    const user = userEvent.setup();
    reset({ queue: [conflict], status });

    render(<OfflinePage />);
    await user.click(screen.getByRole("button", { name: /Note v4/ }));

    fireEvent.change(screen.getByLabelText("Server payload (JSON)"), {
      target: { value: '{"title":"server"}' },
    });
    await user.click(screen.getByLabelText("Review note (optional)"));
    await user.type(screen.getByLabelText("Review note (optional)"), "keeping local title");
    await user.click(screen.getByRole("radio", { name: /Local wins/ }));
    await user.click(screen.getByRole("button", { name: "Apply resolution" }));

    await waitFor(() => {
      expect(controller.resolve).toHaveBeenCalledWith(
        "mut-2",
        expect.objectContaining({
          strategy: "local_wins",
          note: "keeping local title",
        }),
      );
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("wires sync, refresh and clear actions", async () => {
    const user = userEvent.setup();
    reset({
      queue: [pending, { ...pending, id: "mut-synced", status: "synced" }],
      status,
    });

    render(<OfflinePage />);
    await user.click(screen.getByRole("button", { name: /Sync 1 change/ }));
    expect(controller.syncNow).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Refresh queue" }));
    expect(controller.refresh).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Clear synced" }));
    expect(controller.clear).toHaveBeenCalledTimes(1);
  });

  it("surfaces controller failures", () => {
    reset({ error: "Network unreachable" });
    render(<OfflinePage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Network unreachable");
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("disables syncing while offline", () => {
    reset({ online: false, queue: [pending], status });
    render(<OfflinePage />);
    expect(screen.getByRole("button", { name: "Offline" })).toBeDisabled();
    expect(screen.getByText("Reconnect to push queued changes.")).toBeInTheDocument();
  });
});

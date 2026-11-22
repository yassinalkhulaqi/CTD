import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConflictDialog } from "./ConflictDialog";
import { MutationRow } from "./MutationRow";
import { OfflineBadge } from "./OfflineBadge";
import { QueueInspector } from "./QueueInspector";
import { SyncStatus } from "./SyncStatus";
import type { PendingMutation, SyncStatus as SyncStatusModel } from "../types";

const mutation: PendingMutation = {
  id: "mut-abc123",
  client_id: "phone",
  entity: "note",
  operation: "update",
  payload: { title: "Local draft" },
  base_version: 2,
  created_at: "2026-01-01T12:00:00.000Z",
  status: "pending",
  attempts: 1,
  last_error: "",
  resolved_version: null,
  entity_label: "Note",
  is_pending: true,
  next_retry_delay: 2,
};

const conflict: PendingMutation = {
  ...mutation,
  id: "mut-conflict",
  status: "conflict",
  last_error: "version conflict",
};

const synced: PendingMutation = { ...mutation, id: "mut-synced", status: "synced" };

const status: SyncStatusModel = {
  pending: 1,
  synced: 2,
  conflict: 1,
  total: 4,
  attempts: 6,
  backlog: 2,
  completion_rate: 0.5,
  average_attempts: 1.5,
  health_label: "attention",
  has_conflicts: true,
  oldest_pending: mutation.created_at,
  newest_synced: mutation.created_at,
  stale: true,
  resolution_count: 3,
  latest_snapshot: {
    id: "snap-1",
    client_id: "phone",
    synced_at: mutation.created_at,
    version: 7,
    mutation_count: 4,
    conflict_count: 1,
    note: "batch",
    total_count: 5,
    success_rate: 0.8,
  },
};

describe("OfflineBadge", () => {
  it("explains offline, conflict and queued states", () => {
    const { rerender } = render(
      <OfflineBadge online={false} pending={0} conflicts={0} />,
    );
    expect(screen.getByText("Offline")).toBeInTheDocument();

    rerender(<OfflineBadge online pending={0} conflicts={2} />);
    expect(screen.getByText("2 conflicts")).toBeInTheDocument();

    rerender(<OfflineBadge online pending={3} conflicts={0} />);
    expect(screen.getByText("3 queued")).toBeInTheDocument();

    rerender(<OfflineBadge online pending={0} conflicts={0} />);
    expect(screen.getByText("Up to date")).toBeInTheDocument();
  });
});

describe("MutationRow", () => {
  it("exposes mutation details and reports activation", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<MutationRow mutation={conflict} selected onSelect={onSelect} />);

    const row = screen.getByRole("button", {
      name: "Conflict update for Note, base version 2, 1 attempts",
    });
    expect(row).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Updated Note/)).toBeInTheDocument();
    expect(screen.getByText("version conflict")).toBeInTheDocument();
    expect(screen.getByText("Conflict")).toBeInTheDocument();

    await user.click(row);
    expect(onSelect).toHaveBeenCalledWith(conflict);
  });
});

describe("QueueInspector", () => {
  function renderInspector(overrides: Partial<Parameters<typeof QueueInspector>[0]> = {}) {
    const props = {
      mutations: [mutation, conflict, synced],
      loading: false,
      error: null,
      online: true,
      onSelect: vi.fn(),
      onRefresh: vi.fn(),
      onClear: vi.fn(),
      ...overrides,
    };
    const view = render(<QueueInspector {...props} />);
    return { ...props, unmount: view.unmount };
  }

  it("filters the visible mutations by status", async () => {
    const user = userEvent.setup();
    const props = renderInspector();

    expect(screen.getAllByRole("button", { name: /for Note/ })).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: /^Conflicts/ }));
    expect(screen.getAllByRole("button", { name: /for Note/ })).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Refresh queue" }));
    expect(props.onRefresh).toHaveBeenCalledTimes(1);
  });

  it("renders loading, error and empty states", () => {
    const { unmount } = renderInspector({ loading: true, mutations: [] });
    expect(screen.getByLabelText("Loading mutation queue")).toBeInTheDocument();

    unmount();
    renderInspector({ error: "Offline", mutations: [] });
    expect(screen.getByRole("alert")).toHaveTextContent("Offline");

    unmount();
    renderInspector({ mutations: [], online: false });
    expect(screen.getByText("The queue is empty")).toBeInTheDocument();
    expect(screen.getByText(/Your edits are safe/)).toBeInTheDocument();
  });

  it("enables clearing only when synchronised entries exist", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();
    const { unmount } = renderInspector({ mutations: [mutation], onClear });
    expect(screen.getByRole("button", { name: "Clear synced" })).toBeDisabled();

    unmount();
    renderInspector({ mutations: [synced], onClear });
    expect(screen.getByRole("button", { name: "Clear synced" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Clear synced" }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});

describe("SyncStatus", () => {
  it("shows status metrics, progress and the manual sync action", async () => {
    const user = userEvent.setup();
    const onSync = vi.fn();
    render(
      <SyncStatus status={status} online busy={false} onSync={onSync} />,
    );

    expect(screen.getByRole("heading", { name: "Sync status" })).toBeInTheDocument();
    expect(screen.getByText("Conflicts need attention")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
    expect(screen.getByText("Snapshot v7")).toBeInTheDocument();
    expect(screen.getByText("Last sync may be out of date")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Sync 1 change/ }));
    expect(onSync).toHaveBeenCalledTimes(1);
  });

  it("uses an idle state before the status arrives", () => {
    render(<SyncStatus status={null} online={false} busy={false} onSync={vi.fn()} />);
    expect(screen.getByText("Nothing queued yet")).toBeInTheDocument();
    expect(screen.getByText("No changes recorded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Offline" })).toBeDisabled();
  });
});

describe("ConflictDialog", () => {
  it("validates JSON and submits the selected strategy", async () => {
    const user = userEvent.setup();
    const onResolve = vi.fn(async () => true);
    render(
      <ConflictDialog
        mutation={conflict}
        open
        onClose={vi.fn()}
        onResolve={onResolve}
      />,
    );

    const serverField = screen.getByLabelText("Server payload (JSON)");
    fireEvent.change(serverField, { target: { value: "[" } });
    expect(screen.getByRole("alert")).toHaveTextContent("valid JSON objects");
    expect(screen.getByRole("button", { name: "Apply resolution" })).toBeDisabled();

    fireEvent.change(serverField, {
      target: { value: '{"title":"Server note"}' },
    });
    await user.click(screen.getByRole("radio", { name: /Merge fields/ }));
    expect(screen.getByText("Resolved payload preview")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Apply resolution" }));
    expect(onResolve).toHaveBeenCalledWith(
      "mut-conflict",
      "merge",
      "",
      { title: "Server note" },
      {},
    );
  });

  it("renders nothing when closed", () => {
    render(
      <ConflictDialog
        mutation={conflict}
        open={false}
        onClose={vi.fn()}
        onResolve={vi.fn(async () => true)}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

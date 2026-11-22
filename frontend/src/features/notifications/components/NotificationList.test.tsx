/** Rendered notification list interactions. */

import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { NotificationList } from "./NotificationList";
import type { Notification, NotificationFilters } from "../types";

function notification(
  id: string,
  overrides: Partial<Notification> = {},
): Notification {
  return {
    id,
    recipient_id: "member-1",
    channel: "in_app",
    kind: "solve",
    title: `Notification ${id}`,
    body: `Details for ${id}`,
    severity: "info",
    read_at: null,
    created_at: "2026-01-01T10:00:00Z",
    action_url: "",
    is_read: false,
    is_unread: true,
    severity_rank: 0,
    label: "solve · info",
    age_seconds: 10,
    ...overrides,
  };
}

const filters: NotificationFilters = {
  kind: "all",
  severity: "all",
  unreadOnly: false,
  search: "",
};

function renderList(
  overrides: Partial<ComponentProps<typeof NotificationList>> = {},
) {
  const onMarkRead = vi.fn();
  const onMarkAllRead = vi.fn();
  const onFilterChange = vi.fn();
  const onRetry = vi.fn();
  render(
    <NotificationList
      notifications={[
        notification("b", { severity: "critical" }),
        notification("a"),
      ]}
      allNotifications={[
        notification("b", { severity: "critical" }),
        notification("a"),
      ]}
      filters={filters}
      onFilterChange={onFilterChange}
      onMarkRead={onMarkRead}
      onMarkAllRead={onMarkAllRead}
      unread={2}
      loading={false}
      busy={false}
      error={null}
      onRetry={onRetry}
      {...overrides}
    />,
  );
  return { onMarkRead, onMarkAllRead, onFilterChange, onRetry };
}

describe("NotificationList", () => {
  it("renders notifications with severity ordering and an unread badge", () => {
    renderList();
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByLabelText("2 unread")).toHaveTextContent("2");
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveAttribute("data-severity", "critical");
    expect(screen.getByText("Notification a")).toBeInTheDocument();
  });

  it("invokes mark read for the matching notification", () => {
    const { onMarkRead } = renderList();
    fireEvent.click(
      screen.getByRole("button", { name: "Mark Notification a as read" }),
    );
    expect(onMarkRead).toHaveBeenCalledWith("a");
  });

  it("invokes bulk mark read and filter changes", () => {
    const { onMarkAllRead, onFilterChange } = renderList();
    fireEvent.click(screen.getByRole("button", { name: /Mark all read/ }));
    expect(onMarkAllRead).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("switch", { name: /Unread only/ }));
    expect(onFilterChange).toHaveBeenCalledWith("unreadOnly", true);
  });

  it("renders a loading state", () => {
    renderList({ loading: true });
    expect(screen.getByLabelText("Loading notifications")).toBeInTheDocument();
  });

  it("renders an empty state", () => {
    renderList({
      notifications: [],
      allNotifications: [],
      unread: 0,
      loading: false,
    });
    expect(screen.getByText("Nothing to show")).toBeInTheDocument();
  });

  it("renders an error state with retry", () => {
    const { onRetry } = renderList({
      error: "Network is down",
      loading: false,
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Network is down");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("reports search input changes", () => {
    const { onFilterChange } = renderList();
    fireEvent.change(screen.getByLabelText("Search notifications"), {
      target: { value: "flag" },
    });
    expect(onFilterChange).toHaveBeenCalledWith("search", "flag");
  });
});

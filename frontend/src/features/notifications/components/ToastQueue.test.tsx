/** Toast queue rendering and auto-dismiss tests. */

import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useToastQueue } from "../hooks";
import type { Notification, ToastItem } from "../types";
import { ToastQueue } from "./ToastQueue";

function notification(
  id: string,
  severity: Notification["severity"] = "info",
): Notification {
  return {
    id,
    recipient_id: "member-1",
    channel: "in_app",
    kind: "system",
    title: `Toast ${id}`,
    body: "Something happened",
    severity,
    read_at: null,
    created_at: "2026-01-01T10:00:00Z",
    action_url: "",
    is_read: false,
    is_unread: true,
    severity_rank: 0,
    label: "system",
    age_seconds: 0,
  };
}

function toast(
  id: string,
  severity: Notification["severity"] = "info",
): ToastItem {
  return {
    id: `toast-${id}`,
    notification: notification(id, severity),
    tone: severity,
    ttl: 1000,
    createdAt: 0,
  };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("ToastQueue", () => {
  it("renders toasts with the right live region", () => {
    render(
      <ToastQueue
        toasts={[toast("a"), toast("b", "critical")]}
        onDismiss={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    expect(screen.getByTestId("toast-queue")).toBeInTheDocument();
    expect(screen.getByText("Toast a")).toBeInTheDocument();
    expect(screen.getByText("Toast b")).toBeInTheDocument();
    expect(
      screen.getByText("Toast b").closest("[role='alert']"),
    ).not.toBeNull();
  });

  it("dismisses one toast and the whole queue", () => {
    const onDismiss = vi.fn();
    const onClear = vi.fn();
    render(
      <ToastQueue
        toasts={[toast("a"), toast("b")]}
        onDismiss={onDismiss}
        onClear={onClear}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Dismiss Toast a" }));
    expect(onDismiss).toHaveBeenCalledWith("toast-a");
    fireEvent.click(screen.getByRole("button", { name: "Dismiss all toasts" }));
    expect(onClear).toHaveBeenCalled();
  });
});

describe("useToastQueue", () => {
  it("pushes, bounds and auto-dismisses toasts", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToastQueue(2));

    act(() => {
      result.current.push(notification("a"));
      result.current.push(notification("b", "warning"));
      result.current.push(notification("c", "critical"));
    });
    expect(result.current.toasts.map((item) => item.id)).toEqual([
      "toast-b",
      "toast-c",
    ]);

    act(() => {
      vi.advanceTimersByTime(6500);
    });
    expect(result.current.toasts).toHaveLength(0);

    act(() => {
      result.current.push(notification("d"));
      result.current.dismiss("toast-d");
    });
    expect(result.current.toasts).toHaveLength(0);
  });
});

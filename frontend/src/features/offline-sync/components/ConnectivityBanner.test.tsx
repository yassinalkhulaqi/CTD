import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConnectivityBanner } from "./ConnectivityBanner";
import { useOnlineStatus } from "./hooks";

function setOnline(value: boolean): void {
  Object.defineProperty(navigator, "onLine", {
    configurable: true,
    value,
    writable: true,
  });
}

function Probe({ onRetry }: { onRetry?: () => void }) {
  const online = useOnlineStatus();
  return (
    <ConnectivityBanner
      connectivity={online ? "online" : "offline"}
      pending={2}
      onRetry={onRetry}
    />
  );
}

afterEach(() => {
  setOnline(true);
});

describe("ConnectivityBanner", () => {
  it("renders a connected state with an announced status region", () => {
    setOnline(true);
    render(<Probe />);
    const banner = screen.getByRole("status");
    expect(banner).toHaveAttribute("aria-live", "polite");
    expect(banner).toHaveAttribute("data-connectivity", "online");
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("Your workspace is in sync with the server.")).toBeInTheDocument();
  });

  it("reacts to browser offline and online events", () => {
    setOnline(true);
    render(<Probe />);

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByText("You are offline")).toBeInTheDocument();
    expect(screen.getByText("2 changes will sync when you reconnect.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("data-connectivity", "offline");

    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.getByText("Back online")).toBeInTheDocument();
    expect(screen.getByText("2 queued changes ready to sync.")).toBeInTheDocument();
  });

  it("reads navigator.onLine when mounted offline", () => {
    setOnline(false);
    render(<Probe />);
    expect(screen.getByText("You are offline")).toBeInTheDocument();
  });

  it("offers a refresh action only while online", () => {
    setOnline(true);
    const onRetry = vi.fn();
    render(<Probe onRetry={onRetry} />);

    fireEvent.click(screen.getByRole("button", { name: "Refresh sync status" }));
    expect(onRetry).toHaveBeenCalledTimes(1);

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.queryByRole("button", { name: "Refresh sync status" })).toBeNull();
  });
});

/** Countdown ring component tests. */

import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { CountdownRing } from "./CountdownRing";
import type { CtfEvent } from "../types";

function event(overrides: Partial<CtfEvent> = {}): CtfEvent {
  return {
    id: "event-1",
    name: "Finals",
    slug: "finals",
    description: "",
    format: "jeopardy",
    starts_at: "2099-06-01T12:00:00.000Z",
    ends_at: "2099-06-02T12:00:00.000Z",
    status: "upcoming",
    stored_status: "upcoming",
    max_team_size: 4,
    registration_open: true,
    website_url: "",
    tags: [],
    created_at: "2099-01-01T00:00:00.000Z",
    countdown_seconds: 3600,
    countdown_label: "01h 00m",
    seconds_until_start: 3600,
    seconds_remaining: 86400,
    duration_seconds: 86400,
    progress: 0,
    is_live: false,
    is_upcoming: true,
    is_archived: false,
    accepts_registrations: true,
    ...overrides,
  };
}

describe("CountdownRing", () => {
  it("exposes an accessible timer with the formatted countdown", () => {
    render(
      <CountdownRing
        event={event()}
        now={Date.parse("2099-06-01T11:00:00.000Z")}
      />,
    );
    const timer = screenGetTimer();
    expect(timer).toHaveAttribute("aria-label", "Time remaining: 01h 00m");
    expect(timer).toHaveTextContent("01h 00m");
  });

  it("updates when the parent clock advances", () => {
    const before = Date.parse("2099-06-01T11:00:00.000Z");
    const { rerender } = render(<CountdownRing event={event()} now={before} />);
    expect(screenGetTimer()).toHaveTextContent("01h 00m");
    rerender(<CountdownRing event={event()} now={before + 60_000} />);
    expect(screenGetTimer()).toHaveTextContent("59m 00s");
  });

  it("renders a live countdown for a running event", () => {
    render(
      <CountdownRing
        event={event({ status: "live", is_live: true, is_upcoming: false })}
        now={Date.parse("2099-06-01T18:00:00.000Z")}
      />,
    );
    expect(screenGetTimer()).toHaveTextContent("18h 00m");
  });
});

function screenGetTimer(): HTMLElement {
  const timer = document.querySelector('[role="timer"]');
  if (!timer) throw new Error("timer not rendered");
  return timer as HTMLElement;
}

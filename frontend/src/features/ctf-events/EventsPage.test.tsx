/** Rendered interaction tests for the events page. */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { eventsApi } from "./api";
import { EventsPage } from "./EventsPage";
import type { CtfEvent, EventStats, TeamOption } from "./types";

vi.mock("./api", () => ({
  eventsApi: {
    list: vi.fn(),
    allStats: vi.fn(),
    teams: vi.fn(),
    tasks: vi.fn(),
    registrations: vi.fn(),
    register: vi.fn(),
    toggleTask: vi.fn(),
  },
}));

const event: CtfEvent = {
  id: "event-1",
  name: "Autumn Finals",
  slug: "autumn-finals",
  description: "A flagship jeopardy event.",
  format: "jeopardy",
  starts_at: "2099-06-01T12:00:00.000Z",
  ends_at: "2099-06-02T12:00:00.000Z",
  status: "upcoming",
  stored_status: "upcoming",
  max_team_size: 4,
  registration_open: true,
  website_url: "",
  tags: ["web", "crypto"],
  created_at: "2099-01-01T00:00:00.000Z",
  countdown_seconds: 86_400,
  countdown_label: "01d 00h",
  seconds_until_start: 86_400,
  seconds_remaining: 172_800,
  duration_seconds: 86_400,
  progress: 0,
  is_live: false,
  is_upcoming: true,
  is_archived: false,
  accepts_registrations: true,
};

const stats: EventStats = {
  event_id: "event-1",
  capacity: 4,
  confirmed: 2,
  waitlisted: 0,
  cancelled: 0,
  promotions: 0,
  total: 2,
  available_slots: 2,
  is_full: false,
  capacity_ratio: 0.5,
  fill_percentage: 50,
  waitlist_pressure: 0,
};

const teams: TeamOption[] = [
  { id: "team-1", name: "Alpha Squad", slug: "alpha", color: "#6366f1" },
  { id: "team-2", name: "Beta Crew", slug: "beta", color: "#10b981" },
];

describe("EventsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(eventsApi.list).mockImplementation((query = {}) =>
      Promise.resolve({
        events: [event],
        total: 1,
        window: query.window ?? "all",
      }),
    );
    vi.mocked(eventsApi.allStats).mockResolvedValue({ events: [stats] });
    vi.mocked(eventsApi.teams).mockResolvedValue(teams);
    vi.mocked(eventsApi.tasks).mockResolvedValue([]);
    vi.mocked(eventsApi.registrations).mockResolvedValue({
      event_id: "event-1",
      registrations: [],
      confirmed: 2,
      waitlisted: 0,
    });
    vi.mocked(eventsApi.register).mockResolvedValue({
      id: "reg-1",
      event_id: "event-1",
      team_id: "team-1",
      status: "confirmed",
      registered_at: "2099-01-02T00:00:00.000Z",
      is_confirmed: true,
      is_waitlisted: false,
    });
  });

  it("renders the event card, status pill and stats strip", async () => {
    render(<EventsPage />);
    expect(await screen.findByText("Autumn Finals")).toBeInTheDocument();
    expect(
      within(screen.getByRole("article")).getByText("Upcoming"),
    ).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("registers a selected team through the dialog", async () => {
    const user = userEvent.setup();
    render(<EventsPage />);
    await screen.findByText("Autumn Finals");

    await user.click(screen.getByRole("button", { name: "Register" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Team"), "team-1");
    await user.click(
      screen.getByRole("button", { name: /confirm registration/i }),
    );

    await waitFor(() => {
      expect(eventsApi.register).toHaveBeenCalledWith("event-1", "team-1");
    });
    expect(
      await screen.findByText(/Team team-1 is registered for Autumn Finals/i),
    ).toBeInTheDocument();
  });

  it("changes the catalogue window through the filter controls", async () => {
    const user = userEvent.setup();
    render(<EventsPage />);
    await screen.findByText("Autumn Finals");

    await user.click(screen.getByRole("button", { name: /^Live/ }));
    await waitFor(() => {
      expect(
        vi
          .mocked(eventsApi.list)
          .mock.calls.some(([query]) => query?.window === "live"),
      ).toBe(true);
    });
  });

  it("opens the detail drawer with the event checklist", async () => {
    const user = userEvent.setup();
    vi.mocked(eventsApi.tasks).mockResolvedValue([
      {
        id: "task-1",
        event_id: "event-1",
        title: "Book the venue",
        done: false,
        due_at: null,
        is_overdue: false,
      },
    ]);
    render(<EventsPage />);
    await screen.findByText("Autumn Finals");

    await user.click(screen.getByRole("button", { name: /details/i }));
    expect(await screen.findByText("Book the venue")).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: "Book the venue" }),
    ).toBeInTheDocument();
  });
});

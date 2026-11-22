import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.setConfig({ testTimeout: 60_000 });
import type { TimelineController } from "./hooks";
import { groupClusters, singleCluster } from "./logic";
import type {
  ActorSummary,
  TimelineEvent,
  TimelinePage as TimelinePageData,
  TimelineStats,
} from "./types";

const state = vi.hoisted(() => ({ controller: {} as unknown }));

vi.mock("./hooks", () => ({
  useTimeline: () => state.controller,
}));

import { TimelinePage } from "./TimelinePage";

const NOW = "2026-01-05T12:00:00Z";

const event: TimelineEvent = {
  id: "evt-1",
  team_id: "team-1",
  kind: "solve",
  actor_id: "member-1",
  actor_name: "Ada Lovelace",
  summary: "Solved RSA challenge",
  payload_json: '{"points":100}',
  importance: "critical",
  occurred_at: NOW,
  kind_label: "Solve",
  kind_icon: "flag",
  kind_color: "#34d399",
  importance_label: "Critical",
  importance_tone: "danger",
  importance_rank: 3,
  actor_initials: "AL",
  date_key: "2026-01-05",
  hour_key: "2026-01-05T12:00",
  hour_of_day: 12,
  relative_label: "just now",
};

const cluster = singleCluster(event);
const buckets = groupClusters([cluster], new Date(NOW));

const page: TimelinePageData = {
  events: [event],
  clusters: [cluster],
  total: 1,
  limit: 50,
  offset: 0,
  has_more: true,
  next_offset: 1,
  page_number: 1,
};

const stats: TimelineStats = {
  total: 1,
  by_kind: { solve: 1 },
  by_hour: { "2026-01-05T12:00": 1 },
  by_importance: { critical: 1 },
  unique_actors: 1,
  critical_count: 1,
  first_seen: NOW,
  last_seen: NOW,
  generated_at: NOW,
  busiest_kind: "solve",
  busiest_hour: "2026-01-05T12:00",
  critical_ratio: 1,
  average_per_hour: 1,
  top_kinds: [["solve", 1]],
};

const actors: ActorSummary[] = [
  {
    actor_id: "member-1",
    actor_name: "Ada Lovelace",
    event_count: 1,
    critical_count: 1,
    last_seen: NOW,
    kinds: ["solve"],
    label: "Ada Lovelace",
    initials: "AL",
    first_kind: "solve",
  },
];

function controller(
  overrides: Partial<TimelineController> = {},
): TimelineController {
  return {
    page,
    buckets,
    stats,
    actors,
    clusters: [cluster],
    teams: ["team-1", "team-2"],
    loading: false,
    loadingMore: false,
    error: null,
    kinds: ["solve"],
    activeKinds: [],
    activeActors: [],
    activeImportance: [],
    teamId: null,
    pending: 0,
    toggleKind: vi.fn(),
    toggleActor: vi.fn(),
    toggleImportance: vi.fn(),
    setTeamId: vi.fn(),
    clearFilters: vi.fn(),
    refresh: vi.fn(),
    loadMore: vi.fn(),
    showNewEvents: vi.fn(),
    dismissBanner: vi.fn(),
    removeEvent: vi.fn(),
    record: vi.fn(),
    ...overrides,
  };
}

describe("TimelinePage", () => {
  beforeEach(() => {
    state.controller = controller();
  });

  it("renders a loading placeholder", () => {
    state.controller = controller({ loading: true, buckets: [] });
    render(<TimelinePage />);
    expect(
      screen.getByLabelText("Loading activity timeline"),
    ).toBeInTheDocument();
  });

  it("renders an error with a retry action", async () => {
    const user = userEvent.setup();
    const refresh = vi.fn();
    state.controller = controller({ error: "Network unavailable", refresh });
    render(<TimelinePage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Network unavailable");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("renders an empty state for a new workspace", async () => {
    const user = userEvent.setup();
    const refresh = vi.fn();
    state.controller = controller({
      buckets: [],
      page: null,
      stats: null,
      refresh,
    });
    render(<TimelinePage />);
    expect(screen.getByText("No activity yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Check again" }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("renders the stats, filters, banner and grouped list", async () => {
    const user = userEvent.setup();
    const current = controller({ pending: 2 });
    state.controller = current;
    render(<TimelinePage />);

    expect(
      screen.getByRole("heading", { name: "Activity timeline" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Timeline statistics")).toBeInTheDocument();
    expect(screen.getByText("Solved RSA challenge")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("2 new events");

    await user.click(screen.getByRole("button", { name: "Filter by Solves" }));
    expect(current.toggleKind).toHaveBeenCalledWith("solve");
    await user.click(screen.getByRole("button", { name: "Show new events" }));
    expect(current.showNewEvents).toHaveBeenCalledOnce();
    await user.click(
      screen.getByRole("button", { name: "Load older activity" }),
    );
    expect(current.loadMore).toHaveBeenCalledOnce();
    await user.click(
      screen.getByRole("button", { name: "Dismiss event evt-1" }),
    );
    expect(current.removeEvent).toHaveBeenCalledWith("evt-1");
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(current.refresh).toHaveBeenCalledOnce();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.setConfig({ testTimeout: 60_000 });
import { FilterChips } from "./components/FilterChips";
import { GroupHeader } from "./components/GroupHeader";
import { LiveBanner } from "./components/LiveBanner";
import { TimelineItem } from "./components/TimelineItem";
import { TimelineList } from "./components/TimelineList";
import { groupClusters, singleCluster } from "./logic";
import type { ActorSummary, EventCluster, TimelineEvent } from "./types";

const NOW = "2026-01-05T12:00:00Z";

function event(overrides: Partial<TimelineEvent> = {}): TimelineEvent {
  return {
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
    ...overrides,
  };
}

function mergedCluster(): EventCluster {
  return {
    ...singleCluster(event()),
    count: 3,
    is_merged: true,
    count_label: "×3",
    importance_rank: 3,
  };
}

function groups() {
  return groupClusters([mergedCluster()], new Date(NOW));
}

const actor: ActorSummary = {
  actor_id: "member-1",
  actor_name: "Ada Lovelace",
  event_count: 5,
  critical_count: 1,
  last_seen: NOW,
  kinds: ["solve"],
  label: "Ada Lovelace",
  initials: "AL",
  first_kind: "solve",
};

describe("FilterChips", () => {
  it("toggles kind, importance and actor chips and clears filters", async () => {
    const user = userEvent.setup();
    const onToggleKind = vi.fn();
    const onToggleImportance = vi.fn();
    const onToggleActor = vi.fn();
    const onClear = vi.fn();
    render(
      <FilterChips
        kinds={["solve", "note"]}
        activeKinds={["solve"]}
        importance={["low", "normal", "high", "critical"]}
        activeImportance={["critical"]}
        actors={[actor]}
        activeActors={[]}
        teams={["team-1", "team-2"]}
        teamId={null}
        activeCount={2}
        onToggleKind={onToggleKind}
        onToggleImportance={onToggleImportance}
        onToggleActor={onToggleActor}
        onSelectTeam={vi.fn()}
        onClear={onClear}
      />,
    );

    const solve = screen.getByRole("button", { name: "Filter by Solves" });
    expect(solve).toHaveAttribute("aria-pressed", "true");
    await user.click(solve);
    expect(onToggleKind).toHaveBeenCalledWith("solve");

    const critical = screen.getByRole("button", {
      name: "Filter by Critical importance",
    });
    expect(critical).toHaveAttribute("aria-pressed", "true");
    await user.click(critical);
    expect(onToggleImportance).toHaveBeenCalledWith("critical");

    await user.click(
      screen.getByRole("button", { name: "Filter by Ada Lovelace" }),
    );
    expect(onToggleActor).toHaveBeenCalledWith("member-1");

    await user.click(
      screen.getByRole("button", { name: "Clear all timeline filters" }),
    );
    expect(onClear).toHaveBeenCalledOnce();
    expect(
      screen.getByRole("combobox", { name: "Filter by team" }),
    ).toBeInTheDocument();
  });
});

describe("TimelineItem", () => {
  it("renders importance, payload, repeat count and a dismiss action", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<TimelineItem cluster={mergedCluster()} onDismiss={onDismiss} />);

    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("Solved RSA challenge")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("points: 100")).toBeInTheDocument();
    expect(screen.getByText("×3 similar")).toBeInTheDocument();
    expect(screen.getByRole("time")).toHaveAttribute("datetime", NOW);
    await user.click(
      screen.getByRole("button", { name: "Dismiss event evt-1" }),
    );
    expect(onDismiss).toHaveBeenCalledWith("evt-1");
  });

  it("uses the server relative label when no clock is supplied", () => {
    render(<TimelineItem cluster={singleCluster(event())} />);
    expect(screen.getByRole("time")).toHaveTextContent("just now");
  });
});

describe("GroupHeader and TimelineList", () => {
  it("renders day and hour headers with counts", () => {
    const [day] = groups();
    const { rerender } = render(<GroupHeader bucket={day} />);
    expect(
      screen.getByRole("heading", { name: "Today", level: 2 }),
    ).toBeInTheDocument();
    expect(screen.getByText("3 events")).toBeInTheDocument();
    expect(screen.getByText("1 critical")).toBeInTheDocument();

    rerender(<GroupHeader bucket={day.children[0]} compact />);
    expect(
      screen.getByRole("heading", { name: "12:00", level: 3 }),
    ).toBeInTheDocument();
  });

  it("renders a flat list of headers and events with load more", async () => {
    const user = userEvent.setup();
    const onLoadMore = vi.fn();
    render(<TimelineList buckets={groups()} onLoadMore={onLoadMore} />);
    expect(
      screen.getByRole("list", { name: "Activity timeline" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Today" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "12:00" })).toBeInTheDocument();
    expect(screen.getByText("Solved RSA challenge")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Load older activity" }),
    );
    expect(onLoadMore).toHaveBeenCalledOnce();
  });
});

describe("LiveBanner", () => {
  it("announces arrivals and exposes show and dismiss actions", async () => {
    const user = userEvent.setup();
    const onShow = vi.fn();
    const onDismiss = vi.fn();
    const { rerender } = render(
      <LiveBanner count={0} onShow={onShow} onDismiss={onDismiss} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<LiveBanner count={2} onShow={onShow} onDismiss={onDismiss} />);
    expect(screen.getByRole("status")).toHaveTextContent("2 new events");
    await user.click(screen.getByRole("button", { name: "Show new events" }));
    await user.click(
      screen.getByRole("button", { name: "Dismiss new events banner" }),
    );
    expect(onShow).toHaveBeenCalledOnce();
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

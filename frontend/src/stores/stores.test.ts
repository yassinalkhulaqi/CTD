import { beforeEach, describe, expect, it } from "vitest";
import { useActivityStore, matchesFilter } from "./activityStore";
import { useDashboardStore, windowToHours } from "./dashboardStore";
import { useNotificationStore } from "./notificationStore";
import { usePreferencesStore } from "./preferencesStore";
import type { ActivityEvent } from "../types";

function makeEvent(id: number, kind: ActivityEvent["kind"] = "solve.created"): ActivityEvent {
  return {
    id,
    team_id: "team-1",
    kind,
    payload: {},
    occurred_at: new Date(2026, 0, 1, 12, 0, 0).toISOString(),
  };
}

describe("dashboardStore", () => {
  beforeEach(() => {
    useDashboardStore.setState({
      selectedTeamId: null,
      teams: [],
      members: [],
      selectedMemberId: null,
      categoryFilter: "all",
      statusFilter: "all",
      searchQuery: "",
      timeWindow: "24h",
      density: "comfortable",
      sidebarCollapsed: false,
    });
  });

  it("stores and clears the filters", () => {
    const store = useDashboardStore.getState();
    store.setCategoryFilter("web");
    store.setStatusFilter("solved");
    store.setSearchQuery("heap");
    expect(useDashboardStore.getState().categoryFilter).toBe("web");
    expect(useDashboardStore.getState().statusFilter).toBe("solved");

    useDashboardStore.getState().resetFilters();
    expect(useDashboardStore.getState().categoryFilter).toBe("all");
    expect(useDashboardStore.getState().searchQuery).toBe("");
  });

  it("toggles the sidebar", () => {
    expect(useDashboardStore.getState().sidebarCollapsed).toBe(false);
    useDashboardStore.getState().toggleSidebar();
    expect(useDashboardStore.getState().sidebarCollapsed).toBe(true);
  });

  it("keeps the loaded teams", () => {
    useDashboardStore
      .getState()
      .setTeams([{ id: "team-1", name: "RedScribe", slug: "redscribe", color: "#fff", description: "", created_at: "", initials: "RS" }]);
    expect(useDashboardStore.getState().teams).toHaveLength(1);
  });
});

describe("windowToHours", () => {
  it("maps every window to a number of hours", () => {
    expect(windowToHours("6h")).toBe(6);
    expect(windowToHours("12h")).toBe(12);
    expect(windowToHours("24h")).toBe(24);
    expect(windowToHours("7d")).toBe(168);
  });
});

describe("preferencesStore", () => {
  it("clamps the page size", () => {
    usePreferencesStore.getState().setPageSize(1000);
    expect(usePreferencesStore.getState().pageSize).toBe(200);
    usePreferencesStore.getState().setPageSize(1);
    expect(usePreferencesStore.getState().pageSize).toBe(5);
  });

  it("restores the defaults", () => {
    usePreferencesStore.getState().setDensity("compact");
    usePreferencesStore.getState().reset();
    expect(usePreferencesStore.getState().density).toBe("comfortable");
  });
});

describe("activityStore", () => {
  beforeEach(() => {
    useActivityStore.setState({ events: [], missedCount: 0, paused: false, kindFilter: "all" });
  });

  it("prepends events", () => {
    useActivityStore.getState().push(makeEvent(1));
    useActivityStore.getState().push(makeEvent(2));
    expect(useActivityStore.getState().events[0].id).toBe(2);
  });

  it("counts the events missed while paused", () => {
    useActivityStore.getState().setPaused(true);
    useActivityStore.getState().push(makeEvent(1));
    expect(useActivityStore.getState().events).toHaveLength(0);
    expect(useActivityStore.getState().missedCount).toBe(1);
  });

  it("filters the events by kind", () => {
    useActivityStore.getState().push(makeEvent(1, "solve.created"));
    useActivityStore.getState().push(makeEvent(2, "challenge.created"));
    useActivityStore.getState().setKindFilter("solve.created");
    expect(useActivityStore.getState().events.filter((event) => matchesFilter(event, "solve.created"))).toHaveLength(1);
  });

  it("caps the feed size", () => {
    for (let index = 0; index < 260; index += 1) {
      useActivityStore.getState().push(makeEvent(index));
    }
    expect(useActivityStore.getState().events.length).toBeLessThanOrEqual(200);
  });
});

describe("notificationStore", () => {
  beforeEach(() => {
    useNotificationStore.setState({ notifications: [] });
  });

  it("pushes and dismisses notifications", () => {
    const id = useNotificationStore.getState().push({ tone: "info", title: "Hello" });
    expect(useNotificationStore.getState().notifications).toHaveLength(1);
    useNotificationStore.getState().dismiss(id);
    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });

  it("clears every notification", () => {
    useNotificationStore.getState().push({ tone: "info", title: "A" });
    useNotificationStore.getState().push({ tone: "error", title: "B" });
    useNotificationStore.getState().clear();
    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });
});

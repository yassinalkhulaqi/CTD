import { describe, expect, it, vi } from "vitest";

vi.setConfig({ testTimeout: 60_000 });
import {
  activeFilterCount,
  clusterEvents,
  dayKey,
  dayLabel,
  filterEvents,
  flattenBuckets,
  groupClusters,
  hourKey,
  hourLabel,
  importanceLabel,
  importanceRank,
  mergeClusters,
  newEventsSince,
  relativeTime,
  singleCluster,
  sortClusters,
  toneForImportance,
} from "./logic";
import type { EventCluster, Importance, TimelineEvent } from "./types";

const NOW = "2026-01-05T12:00:00Z";
const REFERENCE = new Date(NOW);

function event(overrides: Partial<TimelineEvent> = {}): TimelineEvent {
  return {
    id: "evt-1",
    team_id: "team-1",
    kind: "solve",
    actor_id: "member-1",
    actor_name: "Ada Lovelace",
    summary: "Solved RSA",
    payload_json: '{"points":100}',
    importance: "normal",
    occurred_at: NOW,
    kind_label: "Solve",
    kind_icon: "flag",
    kind_color: "#34d399",
    importance_label: "Normal",
    importance_tone: "info",
    importance_rank: 1,
    actor_initials: "AL",
    date_key: "2026-01-05",
    hour_key: "2026-01-05T12:00",
    hour_of_day: 12,
    relative_label: "just now",
    ...overrides,
  };
}

function cluster(overrides: Partial<EventCluster> = {}): EventCluster {
  return { ...singleCluster(event()), ...overrides };
}

describe("relative time and bucket keys", () => {
  it("formats relative labels with the backend vocabulary", () => {
    expect(relativeTime(NOW, REFERENCE)).toBe("just now");
    expect(relativeTime("2026-01-05T11:57:00Z", REFERENCE)).toBe("3m ago");
    expect(relativeTime("2026-01-05T08:00:00Z", REFERENCE)).toBe("4h ago");
    expect(relativeTime("2026-01-04T12:00:00Z", REFERENCE)).toBe("yesterday");
    expect(relativeTime("2026-01-02T12:00:00Z", REFERENCE)).toBe("3d ago");
    expect(relativeTime("2025-12-24T12:00:00Z", REFERENCE)).toBe("Dec 24");
    expect(relativeTime("not a date", REFERENCE)).toBe("—");
  });

  it("derives stable day and hour keys and labels", () => {
    const moment = "2026-01-05T14:37:00Z";
    expect(dayKey(moment)).toBe("2026-01-05");
    expect(hourKey(moment)).toBe("2026-01-05T14:00");
    expect(hourLabel(moment)).toBe("14:00");
    expect(dayLabel(moment, REFERENCE)).toBe("Today");
    expect(dayLabel("2026-01-04T09:00:00Z", REFERENCE)).toBe("Yesterday");
    expect(dayLabel("2025-12-31T09:00:00Z", REFERENCE)).toBe("Wed, Dec 31");
  });

  it("ranks importance tiers and maps their display metadata", () => {
    const tiers: Importance[] = ["low", "normal", "high", "critical"];
    expect(tiers.map((tier) => importanceRank(tier))).toEqual([0, 1, 2, 3]);
    expect(importanceLabel("critical")).toBe("Critical");
    expect(toneForImportance("critical")).toBe("danger");
    expect(toneForImportance("normal")).toBe("info");
    expect(importanceRank("unknown" as Importance)).toBe(1);
  });
});

describe("clustering and grouping", () => {
  it("collapses consecutive identical events and keeps the strongest", () => {
    const first = event({ id: "evt-1" });
    const duplicate = event({
      id: "evt-2",
      occurred_at: "2026-01-05T11:59:00Z",
    });
    const higher = event({
      id: "evt-3",
      occurred_at: "2026-01-05T11:58:00Z",
      importance: "critical",
      importance_label: "Critical",
      importance_rank: 3,
    });
    const other = event({
      id: "evt-4",
      summary: "Unlocked a hint",
      kind: "hint",
    });
    const clusters = clusterEvents([first, duplicate, higher, other]);
    expect(clusters.map((item) => item.id)).toEqual(["evt-3", "evt-4"]);
    expect(clusters[0].count).toBe(3);
    expect(clusters[0].count_label).toBe("×3");
    expect(clusters[0].is_merged).toBe(true);
    expect(clusters[0].event.importance).toBe("critical");
    expect(clusters[0].last_at).toBe("2026-01-05T11:58:00Z");
    expect(clusterEvents([first, duplicate], 5)).toHaveLength(2);
    expect(clusterEvents([])).toEqual([]);
  });

  it("groups clusters into day and hour buckets", () => {
    const early = cluster({
      event: event({ id: "evt-1", occurred_at: "2026-01-05T10:10:00Z" }),
      first_at: "2026-01-05T10:10:00Z",
      last_at: "2026-01-05T10:10:00Z",
    });
    const late = cluster({
      event: event({
        id: "evt-2",
        occurred_at: "2026-01-05T11:40:00Z",
        importance: "critical",
        importance_rank: 3,
      }),
      first_at: "2026-01-05T11:40:00Z",
      last_at: "2026-01-05T11:40:00Z",
      importance_rank: 3,
    });
    const older = cluster({
      event: event({ id: "evt-3", occurred_at: "2026-01-04T09:00:00Z" }),
      first_at: "2026-01-04T09:00:00Z",
      last_at: "2026-01-04T09:00:00Z",
    });
    const groups = groupClusters(sortClusters([early, late, older]), REFERENCE);
    expect(groups.map((group) => group.key)).toEqual([
      "2026-01-05",
      "2026-01-04",
    ]);
    expect(groups[0].label).toBe("Today");
    expect(groups[0].children.map((child) => child.label)).toEqual([
      "11:00",
      "10:00",
    ]);
    expect(groups[0].count).toBe(2);
    expect(groups[0].critical_count).toBe(1);
    expect(groups[0].peak_importance).toBe("critical");
    expect(groups[1].children[0].label).toBe("09:00");
  });

  it("flattens buckets into ordered list rows", () => {
    const groups = groupClusters([cluster()], REFERENCE);
    const rows = flattenBuckets(groups);
    expect(rows.map((row) => row.type)).toEqual(["day", "hour", "event"]);
    expect(rows[0].key).toBe("day:2026-01-05");
    expect(rows[1].key).toBe("hour:2026-01-05T12:00");
    expect(rows[2].key).toBe("event:evt-1");
  });
});

describe("filters and live updates", () => {
  it("filters events by every supported criterion", () => {
    const events = [
      event(),
      event({
        id: "evt-2",
        kind: "note",
        actor_id: "member-2",
        team_id: "team-2",
        importance: "critical",
        occurred_at: "2026-01-04T10:00:00Z",
      }),
    ];
    expect(
      filterEvents(events, { kinds: ["note"] }).map((item) => item.id),
    ).toEqual(["evt-2"]);
    expect(filterEvents(events, { actors: ["member-1"] })).toHaveLength(1);
    expect(filterEvents(events, { importance: ["critical"] })).toHaveLength(1);
    expect(filterEvents(events, { teamId: "team-2" })).toHaveLength(1);
    expect(filterEvents(events, { from: "2026-01-05T00:00:00Z" })).toHaveLength(
      1,
    );
    expect(filterEvents(events, { to: "2026-01-04T23:00:00Z" })).toHaveLength(
      1,
    );
    expect(
      activeFilterCount({ kinds: ["solve"], actors: ["m1"], teamId: "t1" }),
    ).toBe(3);
  });

  it("detects arrivals and merges paged clusters", () => {
    const newest = event({ id: "evt-new" });
    const seen = event({ id: "evt-seen" });
    expect(newEventsSince([newest, seen], "evt-seen")).toEqual([newest]);
    expect(newEventsSince([newest], null)).toEqual([]);
    expect(newEventsSince([newest], "evt-missing")).toEqual([newest]);
    const merged = mergeClusters(
      [cluster()],
      [cluster(), cluster({ id: "evt-2" })],
    );
    expect(merged.map((item) => item.id)).toEqual(["evt-1", "evt-2"]);
  });
});

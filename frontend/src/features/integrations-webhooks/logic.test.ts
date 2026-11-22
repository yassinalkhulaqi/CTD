import { describe, expect, it } from "vitest";
import {
  deliveryTone,
  eventLabel,
  eventMapEntries,
  formatTimestamp,
  hasMappings,
  isValidEndpointUrl,
  kindLabel,
  maskDisplay,
  normaliseEvents,
  percentage,
  retryLabel,
  summariseStats,
  topEvents,
  validateDraft,
} from "./logic";
import { EMPTY_DRAFT, type Adapter, type IntegrationStats } from "./types";

const stats: IntegrationStats = {
  total_integrations: 2,
  enabled_integrations: 1,
  total_adapters: 1,
  total_deliveries: 4,
  pending_deliveries: 1,
  successful_deliveries: 2,
  failed_deliveries: 1,
  success_rate: 0.5,
  failure_rate: 0.25,
  average_attempts: 1.5,
  last_sent_at: "2026-01-02T03:04:05Z",
  by_event: { "challenge.solved": 3, "score.changed": 1 },
  by_kind: { webhook: 2 },
};

describe("endpoint validation", () => {
  it("accepts http and https endpoints", () => {
    expect(isValidEndpointUrl("https://example.com/hook")).toBe(true);
    expect(isValidEndpointUrl(" http://localhost:9000/path ")).toBe(true);
  });

  it("rejects unsafe or malformed endpoints", () => {
    expect(isValidEndpointUrl("ftp://example.com")).toBe(false);
    expect(isValidEndpointUrl("https://user:pass@example.com")).toBe(false);
    expect(isValidEndpointUrl("https://example.com/#frag")).toBe(false);
    expect(isValidEndpointUrl("not a url")).toBe(false);
  });
});

describe("secret and event helpers", () => {
  it("masks the middle of a secret", () => {
    expect(maskDisplay("abcdefghijkl")).toBe("ab••••••••kl");
    expect(maskDisplay("abc")).toBe("•••");
    expect(maskDisplay("")).toBe("");
  });

  it("normalises events against the allowlist", () => {
    expect(
      normaliseEvents(["Challenge.Solved", "challenge.solved", "unknown", ""]),
    ).toEqual(["challenge.solved"]);
  });

  it("labels events and transports", () => {
    expect(eventLabel("challenge.solved")).toBe("Challenge solved");
    expect(eventLabel("custom.event")).toBe("custom.event");
    expect(kindLabel("ctf_platform")).toBe("CTF platform");
  });
});

describe("formatting helpers", () => {
  it("maps delivery statuses to badge tones", () => {
    expect(deliveryTone("success")).toBe("success");
    expect(deliveryTone("failed")).toBe("danger");
    expect(deliveryTone("pending")).toBe("warning");
  });

  it("formats timestamps and ratios", () => {
    expect(formatTimestamp(null)).toBe("—");
    expect(formatTimestamp("invalid")).toBe("—");
    expect(formatTimestamp("2026-01-02T03:04:05Z")).not.toBe("—");
    expect(percentage(0.456)).toBe("46%");
    expect(retryLabel(16)).toBe("16s");
    expect(retryLabel(120)).toBe("2m");
  });

  it("sorts adapter entries and events", () => {
    expect(
      eventMapEntries({ "score.changed": "b", "challenge.solved": "a" }),
    ).toEqual([
      ["challenge.solved", "a"],
      ["score.changed", "b"],
    ]);
    expect(topEvents(stats, 1)).toEqual([["challenge.solved", 3]]);
  });

  it("summarises statistics", () => {
    expect(summariseStats(stats)).toBe("2 of 4 deliveries succeeded");
    expect(
      summariseStats({
        ...stats,
        total_deliveries: 0,
        successful_deliveries: 0,
      }),
    ).toBe("No deliveries recorded yet");
  });
});

describe("draft validation", () => {
  it("accepts a complete draft", () => {
    expect(
      validateDraft({
        ...EMPTY_DRAFT,
        name: "Alerts",
        endpoint_url: "https://example.com/hook",
      }),
    ).toEqual({});
  });

  it("reports every invalid field", () => {
    const errors = validateDraft({
      ...EMPTY_DRAFT,
      name: "",
      endpoint_url: "file:///tmp/hook",
      events: [],
      secret: "short",
    });
    expect(Object.keys(errors).sort()).toEqual([
      "endpoint_url",
      "events",
      "name",
      "secret",
    ]);
  });

  it("detects adapters with mappings", () => {
    const adapter: Adapter = {
      id: "adt-1",
      name: "Bridge",
      event_map: {},
      mapping_count: 0,
      created_at: "2026-01-02T03:04:05Z",
    };
    expect(hasMappings(adapter)).toBe(false);
    expect(hasMappings({ ...adapter, mapping_count: 1 })).toBe(true);
  });
});

import { describe, expect, it } from "vitest";
import {
  STRATEGY_OPTIONS,
  buildCurrentVersions,
  completionText,
  conflictedMutations,
  connectivityCopy,
  describeMutation,
  formatAge,
  formatAttempts,
  groupMutations,
  healthLabel,
  healthTone,
  isValidStrategy,
  mergePreview,
  operationLabel,
  operationTone,
  parseJsonObject,
  payloadPreview,
  sortMutations,
  statusLabel,
  statusTone,
  summariseQueue,
  syncButtonLabel,
} from "./sync";
import type { PendingMutation, SyncStatus } from "./types";

function mutation(
  id: string,
  overrides: Partial<PendingMutation> = {},
): PendingMutation {
  return {
    id,
    client_id: "client-a",
    entity: "note",
    operation: "update",
    payload: { title: "Draft" },
    base_version: 2,
    created_at: "2026-01-01T12:00:00.000Z",
    status: "pending",
    attempts: 0,
    last_error: "",
    resolved_version: null,
    entity_label: "Note",
    is_pending: true,
    next_retry_delay: 2,
    ...overrides,
  };
}

function status(overrides: Partial<SyncStatus> = {}): SyncStatus {
  return {
    pending: 2,
    synced: 6,
    conflict: 1,
    total: 9,
    attempts: 12,
    backlog: 3,
    completion_rate: 2 / 3,
    average_attempts: 1.33,
    health_label: "attention",
    has_conflicts: true,
    oldest_pending: "2026-01-01T12:00:00.000Z",
    newest_synced: "2026-01-01T11:00:00.000Z",
    stale: false,
    resolution_count: 4,
    latest_snapshot: null,
    ...overrides,
  };
}

describe("status presentation helpers", () => {
  it("maps statuses and operations onto tones and labels", () => {
    expect(statusTone("synced")).toBe("success");
    expect(statusTone("conflict")).toBe("danger");
    expect(statusTone("pending")).toBe("warning");
    expect(statusLabel("pending")).toBe("Pending");
    expect(operationTone("create")).toBe("success");
    expect(operationTone("delete")).toBe("danger");
    expect(operationLabel("update")).toBe("Updated");
  });

  it("maps health labels onto copy and tones", () => {
    expect(healthTone("healthy")).toBe("success");
    expect(healthTone("attention")).toBe("danger");
    expect(healthTone("syncing")).toBe("info");
    expect(healthLabel("idle")).toBe("Nothing queued yet");
    expect(healthLabel("attention")).toContain("Conflicts");
  });

  it("describes connectivity for all states", () => {
    const offline = connectivityCopy(false, 3);
    expect(offline.title).toBe("You are offline");
    expect(offline.detail).toContain("3 changes");
    expect(connectivityCopy(false, 0).detail).toContain("queued locally");
    expect(connectivityCopy(true, 1).title).toBe("Back online");
    expect(connectivityCopy(true, 0).tone).toBe("success");
  });

  it("recognises only the supported strategies", () => {
    expect(isValidStrategy("merge")).toBe(true);
    expect(isValidStrategy("local_wins")).toBe(true);
    expect(isValidStrategy("teleport")).toBe(false);
    expect(STRATEGY_OPTIONS).toHaveLength(3);
  });
});

describe("queue helpers", () => {
  it("groups, counts and filters mutations", () => {
    const items = [
      mutation("a"),
      mutation("b", { status: "synced" }),
      mutation("c", { status: "conflict" }),
      mutation("d", { status: "conflict" }),
    ];
    const grouped = groupMutations(items);
    expect(grouped.pending).toHaveLength(1);
    expect(grouped.synced).toHaveLength(1);
    expect(grouped.conflict).toHaveLength(2);
    expect(summariseQueue(items)).toEqual({
      pending: 1,
      synced: 1,
      conflict: 2,
      total: 4,
    });
    expect(conflictedMutations(items).map((item) => item.id)).toEqual(["c", "d"]);
  });

  it("sorts by creation time and identifier", () => {
    const items = [
      mutation("b", { created_at: "2026-01-01T12:00:00.000Z" }),
      mutation("a", { created_at: "2026-01-02T12:00:00.000Z" }),
      mutation("c", { created_at: "2026-01-01T12:00:00.000Z" }),
    ];
    expect(sortMutations(items).map((item) => item.id)).toEqual(["b", "c", "a"]);
    expect(sortMutations(items, true).map((item) => item.id)).toEqual(["a", "c", "b"]);
  });

  it("infers the highest known version per entity", () => {
    const versions = buildCurrentVersions([
      mutation("a", { entity: "note", base_version: 3 }),
      mutation("b", { entity: "note", base_version: 7 }),
      mutation("c", { entity: "challenge", base_version: 1 }),
    ]);
    expect(versions).toEqual({ note: 7, challenge: 1 });
  });

  it("formats accessible row descriptions and previews", () => {
    const item = mutation("a", { attempts: 2 });
    expect(describeMutation(item)).toContain("Pending update for Note");
    expect(describeMutation(item)).toContain("2 attempts");
    expect(payloadPreview({ title: "Short" })).toBe('{"title":"Short"}');
    expect(payloadPreview({ value: "x".repeat(200) }, 20)).toHaveLength(20);
    expect(formatAttempts(0)).toBe("Not attempted");
    expect(formatAttempts(1)).toBe("1 attempt");
    expect(
      formatAge("2026-01-01T12:00:00.000Z", new Date("2026-01-01T12:05:00.000Z")),
    ).toBe("5 minutes ago");
  });

  it("formats completion and sync button copy", () => {
    expect(completionText(status())).toBe("67% complete");
    expect(completionText(status({ total: 0 }))).toBe("No changes recorded");
    expect(completionText(null)).toBe("No changes recorded");
    expect(syncButtonLabel(false, false, 3)).toBe("Offline");
    expect(syncButtonLabel(true, true, 3)).toBe("Syncing…");
    expect(syncButtonLabel(true, false, 0)).toBe("Sync now");
    expect(syncButtonLabel(true, false, 2)).toBe("Sync 2 changes");
  });
});

describe("JSON payload helpers", () => {
  it("parses objects and rejects invalid input", () => {
    expect(parseJsonObject("")).toEqual({ ok: true, value: {} });
    expect(parseJsonObject('{"title":"ok"}')).toEqual({
      ok: true,
      value: { title: "ok" },
    });
    expect(parseJsonObject("[").ok).toBe(false);
    expect(parseJsonObject("[1,2]").ok).toBe(false);
  });

  it("previews local wins and remote wins", () => {
    const base = { title: "old" };
    const local = { title: "local", localOnly: 1 };
    const remote = { title: "remote", remoteOnly: 2 };
    expect(mergePreview(base, local, remote, "local_wins").payload).toEqual({
      title: "local",
      remoteOnly: 2,
      localOnly: 1,
    });
    expect(mergePreview(base, local, remote, "remote_wins").payload).toEqual({
      localOnly: 1,
      title: "remote",
      remoteOnly: 2,
    });
  });

  it("performs a three-way merge and flags contested fields", () => {
    const preview = mergePreview(
      { title: "old", body: "shared" },
      { title: "local", body: "shared" },
      { title: "remote", body: "server edit" },
      "merge",
    );
    expect(preview.payload).toEqual({ title: "local", body: "server edit" });
    expect(preview.contested).toEqual(["title"]);
    expect(preview.fields).toEqual(["body", "title"]);
  });

  it("keeps a clean merge free of contested fields", () => {
    const preview = mergePreview(
      { title: "old", body: "shared" },
      { title: "local", body: "shared" },
      { title: "old", body: "server edit" },
      "merge",
    );
    expect(preview.contested).toEqual([]);
    expect(preview.payload).toEqual({ title: "local", body: "server edit" });
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";
import type * as ClientModule from "../../api/client";
import type { ClearResponse, ConflictResolution, PendingMutation, ProcessResponse, QueueResponse, SyncStatus } from "./types";

const mockGet = vi.hoisted(() => vi.fn());
const mockPost = vi.hoisted(() => vi.fn());
const mockDel = vi.hoisted(() => vi.fn());

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof ClientModule>();
  return { ...actual, get: mockGet, post: mockPost, del: mockDel };
});

import { offlineSyncApi } from "./api";

const mutation: PendingMutation = {
  id: "mut-1",
  client_id: "phone",
  entity: "note",
  operation: "update",
  payload: { title: "Draft" },
  base_version: 1,
  created_at: "2026-01-01T12:00:00.000Z",
  status: "pending",
  attempts: 0,
  last_error: "",
  resolved_version: null,
  entity_label: "Note",
  is_pending: true,
  next_retry_delay: 2,
};

const queue: QueueResponse = {
  client_id: null,
  items: [mutation],
  total: 1,
  pending: 1,
  conflicts: 0,
  oldest_first: true,
};

const status: SyncStatus = {
  pending: 1,
  synced: 0,
  conflict: 0,
  total: 1,
  attempts: 0,
  backlog: 1,
  completion_rate: 0,
  average_attempts: 0,
  health_label: "syncing",
  has_conflicts: false,
  oldest_pending: mutation.created_at,
  newest_synced: null,
  stale: false,
  resolution_count: 0,
  latest_snapshot: null,
};

const processResponse: ProcessResponse = {
  outcomes: [],
  processed: 0,
  applied: 0,
  conflicts: 0,
  skipped: 0,
  failed: 0,
  success_rate: 1,
  started_at: mutation.created_at,
  finished_at: mutation.created_at,
  snapshot: null,
};

describe("offlineSyncApi", () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockDel.mockReset();
  });

  it("enqueues a mutation through POST", async () => {
    mockPost.mockResolvedValue(mutation);
    const result = await offlineSyncApi.enqueue({
      client_id: "phone",
      entity: "note",
      operation: "update",
      payload: { title: "Draft" },
      base_version: 1,
    });
    expect(result).toEqual(mutation);
    expect(mockPost).toHaveBeenCalledWith(
      "/api/sync/mutations",
      {
        client_id: "phone",
        entity: "note",
        operation: "update",
        payload: { title: "Draft" },
        base_version: 1,
      },
      undefined,
    );
  });

  it("builds queue filters into the query string", async () => {
    mockGet.mockResolvedValue(queue);
    const result = await offlineSyncApi.listQueue({
      clientId: "phone",
      status: "conflict",
      entity: "note",
      limit: 20,
    });
    expect(result).toEqual(queue);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/sync/queue?client_id=phone&status=conflict&entity=note&limit=20",
      undefined,
    );
  });

  it("omits empty queue filters", async () => {
    mockGet.mockResolvedValue(queue);
    await offlineSyncApi.listQueue();
    expect(mockGet).toHaveBeenCalledWith("/api/sync/queue", undefined);
  });

  it("posts a processing batch", async () => {
    mockPost.mockResolvedValue(processResponse);
    const result = await offlineSyncApi.process({
      client_id: "phone",
      limit: 10,
      current_versions: { note: 4 },
    });
    expect(result).toEqual(processResponse);
    expect(mockPost).toHaveBeenCalledWith(
      "/api/sync/process",
      { client_id: "phone", limit: 10, current_versions: { note: 4 } },
      undefined,
    );
  });

  it("encodes the mutation id in the resolve path", async () => {
    const resolution = { id: "res-1", mutation_id: "mut 1" } as ConflictResolution;
    mockPost.mockResolvedValue(resolution);
    await offlineSyncApi.resolveConflict("mut 1", {
      strategy: "merge",
      note: "reviewed",
    });
    expect(mockPost).toHaveBeenCalledWith(
      "/api/sync/conflicts/mut%201/resolve",
      { strategy: "merge", note: "reviewed" },
      undefined,
    );
  });

  it("reads status and clears synced entries with scoped clients", async () => {
    const cleared: ClearResponse = { client_id: "phone", deleted: 2, remaining: 1 };
    mockGet.mockResolvedValue(status);
    mockDel.mockResolvedValue(cleared);

    expect(await offlineSyncApi.status("phone")).toEqual(status);
    expect(mockGet).toHaveBeenCalledWith("/api/sync/status?client_id=phone", undefined);
    expect(await offlineSyncApi.clearSynced("phone")).toEqual(cleared);
    expect(mockDel).toHaveBeenCalledWith("/api/sync/queue?client_id=phone", undefined);
  });
});

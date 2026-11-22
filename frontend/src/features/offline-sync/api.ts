/**
 * Typed HTTP adapter for the offline synchronisation endpoints.
 */

import {
  buildQuery,
  del,
  get,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  ClearResponse,
  ConflictResolveRequest,
  ConflictResolution,
  MutationCreate,
  PendingMutation,
  ProcessRequest,
  ProcessResponse,
  QueueFilters,
  QueueResponse,
  SyncStatus,
} from "./types";

/** The sync endpoints used by the Offline & Sync screen. */
export const offlineSyncApi = {
  /**
   * Enqueue a locally captured mutation.
   *
   * @param payload - Mutation fields produced by the client.
   * @param options - Request options such as an abort signal.
   * @returns The newly queued mutation.
   */
  enqueue(
    payload: MutationCreate,
    options?: RequestOptions,
  ): Promise<PendingMutation> {
    return post<PendingMutation>("/api/sync/mutations", payload, options);
  },

  /**
   * Return the queue with optional filters.
   *
   * @param filters - Client, status, entity and limit filters.
   * @param options - Request options.
   * @returns The queue response.
   */
  listQueue(
    filters: QueueFilters = {},
    options?: RequestOptions,
  ): Promise<QueueResponse> {
    const query = buildQuery({
      client_id: filters.clientId,
      status: filters.status,
      entity: filters.entity,
      limit: filters.limit,
    });
    return get<QueueResponse>(`/api/sync/queue${query}`, options);
  },

  /**
   * Process one batch against the supplied server versions.
   *
   * @param request - Batch size, client filter and version snapshot.
   * @param options - Request options.
   * @returns The batch report.
   */
  process(
    request: ProcessRequest,
    options?: RequestOptions,
  ): Promise<ProcessResponse> {
    return post<ProcessResponse>("/api/sync/process", request, options);
  },

  /**
   * Resolve a conflicted mutation with a chosen strategy.
   *
   * @param mutationId - Identifier of the conflicting mutation.
   * @param request - Strategy, note and optional payload snapshots.
   * @param options - Request options.
   * @returns The persisted resolution.
   */
  resolveConflict(
    mutationId: string,
    request: ConflictResolveRequest,
    options?: RequestOptions,
  ): Promise<ConflictResolution> {
    return post<ConflictResolution>(
      `/api/sync/conflicts/${encodeURIComponent(mutationId)}/resolve`,
      request,
      options,
    );
  },

  /**
   * Read queue health and snapshot freshness.
   *
   * @param clientId - Optional client filter.
   * @param options - Request options.
   * @returns The status summary.
   */
  status(
    clientId?: string,
    options?: RequestOptions,
  ): Promise<SyncStatus> {
    const query = buildQuery({ client_id: clientId });
    return get<SyncStatus>(`/api/sync/status${query}`, options);
  },

  /**
   * Remove synchronised queue entries.
   *
   * @param clientId - Optional client filter.
   * @param options - Request options.
   * @returns The deletion summary.
   */
  clearSynced(
    clientId?: string,
    options?: RequestOptions,
  ): Promise<ClearResponse> {
    const query = buildQuery({ client_id: clientId });
    return del<ClearResponse>(`/api/sync/queue${query}`, options);
  },
};

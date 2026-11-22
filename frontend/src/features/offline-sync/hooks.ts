/**
 * Data loading and interaction state for the Offline & Sync screen.
 */

import { useCallback, useEffect, useState } from "react";
import { toApiError } from "../../api/client";
import { offlineSyncApi } from "./api";
import { buildCurrentVersions } from "./sync";
import type {
  ConflictResolveRequest,
  PendingMutation,
  ProcessResponse,
  SyncStatus,
} from "./types";

/** Combined state and actions used by the offline page. */
export interface OfflineSyncController {
  /** Mutations currently held in the queue. */
  queue: PendingMutation[];
  /** Queue health summary, or `null` before the first load. */
  status: SyncStatus | null;
  /** Whether the initial load is in flight. */
  loading: boolean;
  /** Whether a sync, resolve or clear action is in flight. */
  busy: boolean;
  /** Browser connectivity state. */
  online: boolean;
  /** Last human readable failure, or `null`. */
  error: string | null;
  /** Reload the queue and status. */
  refresh: () => Promise<void>;
  /** Process a batch using the supplied or inferred server versions. */
  syncNow: (
    currentVersions?: Record<string, number>,
  ) => Promise<ProcessResponse | null>;
  /** Resolve a conflicted mutation and refresh the queue. */
  resolve: (
    mutationId: string,
    request: ConflictResolveRequest,
  ) => Promise<boolean>;
  /** Clear synchronised entries and refresh the queue. */
  clear: () => Promise<boolean>;
  /** Clear a displayed error without touching the network. */
  dismissError: () => void;
}

/**
 * Track browser connectivity through `navigator.onLine` and window events.
 *
 * @returns `true` when the browser reports a usable connection.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );

  useEffect(() => {
    const markOnline = () => setOnline(true);
    const markOffline = () => setOnline(false);
    window.addEventListener("online", markOnline);
    window.addEventListener("offline", markOffline);
    setOnline(navigator.onLine);
    return () => {
      window.removeEventListener("online", markOnline);
      window.removeEventListener("offline", markOffline);
    };
  }, []);

  return online;
}

/**
 * Load sync state and expose the actions used by the page components.
 *
 * Reconnecting automatically refreshes both resources so queued work appears
 * without a manual reload. Failures are surfaced as messages rather than
 * thrown, keeping the screen usable when the API is unreachable.
 *
 * @param clientId - Optional client whose queue should be displayed.
 * @returns The controller consumed by {@link OfflinePage}.
 */
export function useOfflineSync(clientId?: string): OfflineSyncController {
  const online = useOnlineStatus();
  const [queue, setQueue] = useState<PendingMutation[]>([]);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [queueResponse, statusResponse] = await Promise.all([
        offlineSyncApi.listQueue(clientId ? { clientId } : {}),
        offlineSyncApi.status(clientId),
      ]);
      setQueue(queueResponse.items);
      setStatus(statusResponse);
    } catch (cause) {
      setError(toApiError(cause).message);
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    if (!online) {
      setLoading(false);
      return;
    }
    void refresh();
  }, [refresh, online]);

  const syncNow = useCallback(
    async (currentVersions?: Record<string, number>) => {
      if (!online) {
        setError("You are offline. Reconnect before syncing.");
        return null;
      }
      setBusy(true);
      setError(null);
      try {
        const result = await offlineSyncApi.process({
          client_id: clientId,
          current_versions: currentVersions ?? buildCurrentVersions(queue),
        });
        await refresh();
        return result;
      } catch (cause) {
        setError(toApiError(cause).message);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [clientId, online, queue, refresh],
  );

  const resolve = useCallback(
    async (mutationId: string, request: ConflictResolveRequest) => {
      setBusy(true);
      setError(null);
      try {
        await offlineSyncApi.resolveConflict(mutationId, request);
        await refresh();
        return true;
      } catch (cause) {
        setError(toApiError(cause).message);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const clear = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await offlineSyncApi.clearSynced(clientId);
      await refresh();
      return true;
    } catch (cause) {
      setError(toApiError(cause).message);
      return false;
    } finally {
      setBusy(false);
    }
  }, [clientId, refresh]);

  const dismissError = useCallback(() => setError(null), []);

  return {
    queue,
    status,
    loading,
    busy,
    online,
    error,
    refresh,
    syncNow,
    resolve,
    clear,
    dismissError,
  };
}

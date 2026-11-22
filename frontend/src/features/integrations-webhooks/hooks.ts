/**
 * Data loading and mutation helpers for the integrations screen.
 */

import { useCallback, useEffect, useState } from "react";
import * as api from "./api";
import type {
  Adapter,
  AdapterCreateInput,
  Delivery,
  DispatchInput,
  Integration,
  IntegrationCreateInput,
  IntegrationStats,
  IntegrationUpdateInput,
  SimulationInput,
} from "./types";

/** Convert an unknown failure into a short user facing message. */
export function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Something went wrong";
}

/** Everything the integrations page needs from the API. */
export interface IntegrationsController {
  integrations: Integration[];
  deliveries: Delivery[];
  adapters: Adapter[];
  stats: IntegrationStats | null;
  loading: boolean;
  busy: string | null;
  error: string | null;
  refresh: () => Promise<void>;
  create: (input: IntegrationCreateInput) => Promise<void>;
  update: (id: string, input: IntegrationUpdateInput) => Promise<void>;
  remove: (id: string) => Promise<void>;
  dispatch: (input: DispatchInput) => Promise<void>;
  retry: (id: string) => Promise<void>;
  simulate: (id: string, input: SimulationInput) => Promise<void>;
  addAdapter: (input: AdapterCreateInput) => Promise<void>;
  removeAdapter: (id: string) => Promise<void>;
  clearError: () => void;
}

/** Load and mutate all integration data with consistent error handling. */
export function useIntegrations(): IntegrationsController {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [stats, setStats] = useState<IntegrationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (quiet = false): Promise<void> => {
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const [nextIntegrations, nextDeliveries, nextAdapters, nextStats] =
        await Promise.all([
          api.fetchIntegrations(),
          api.fetchDeliveries(),
          api.fetchAdapters(),
          api.fetchStats(),
        ]);
      setIntegrations(nextIntegrations);
      setDeliveries(nextDeliveries);
      setAdapters(nextAdapters);
      setStats(nextStats);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = useCallback(
    async (key: string, task: () => Promise<void>): Promise<void> => {
      setBusy(key);
      setError(null);
      try {
        await task();
        await refresh(true);
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setBusy(null);
      }
    },
    [refresh],
  );

  const create = useCallback(
    (input: IntegrationCreateInput) =>
      run("create", async () => {
        await api.createIntegration(input);
      }),
    [run],
  );

  const update = useCallback(
    (id: string, input: IntegrationUpdateInput) =>
      run(`update-${id}`, async () => {
        await api.updateIntegration(id, input);
      }),
    [run],
  );

  const remove = useCallback(
    (id: string) =>
      run(`delete-${id}`, async () => {
        await api.deleteIntegration(id);
      }),
    [run],
  );

  const dispatch = useCallback(
    (input: DispatchInput) =>
      run("dispatch", async () => {
        await api.dispatchEvent(input);
      }),
    [run],
  );

  const retry = useCallback(
    (id: string) =>
      run(`retry-${id}`, async () => {
        await api.retryDelivery(id);
      }),
    [run],
  );

  const simulate = useCallback(
    (id: string, input: SimulationInput) =>
      run(`simulate-${id}`, async () => {
        await api.simulateDelivery(id, input);
      }),
    [run],
  );

  const addAdapter = useCallback(
    (input: AdapterCreateInput) =>
      run("adapter", async () => {
        await api.createAdapter(input);
      }),
    [run],
  );

  const removeAdapter = useCallback(
    (id: string) =>
      run(`adapter-${id}`, async () => {
        await api.deleteAdapter(id);
      }),
    [run],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    integrations,
    deliveries,
    adapters,
    stats,
    loading,
    busy,
    error,
    refresh: () => refresh(),
    create,
    update,
    remove,
    dispatch,
    retry,
    simulate,
    addAdapter,
    removeAdapter,
    clearError,
  };
}

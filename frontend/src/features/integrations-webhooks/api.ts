/**
 * Typed API adapter for the integrations feature.
 */

import { buildQuery, del, get, patch, post } from "../../api/client";
import type {
  Adapter,
  AdapterCreateInput,
  Delivery,
  DeliveryStatus,
  DispatchInput,
  Integration,
  IntegrationCreateInput,
  IntegrationStats,
  IntegrationUpdateInput,
  SimulationInput,
} from "./types";

const BASE = "/api/integrations";

function integrationPath(id: string): string {
  return `${BASE}/${encodeURIComponent(id)}`;
}

/** Return every configured integration. */
export function fetchIntegrations(): Promise<Integration[]> {
  return get<Integration[]>(BASE);
}

/** Return one integration by identifier. */
export function fetchIntegration(id: string): Promise<Integration> {
  return get<Integration>(integrationPath(id));
}

/** Register a new integration. */
export function createIntegration(
  input: IntegrationCreateInput,
): Promise<Integration> {
  return post<Integration>(BASE, input);
}

/** Update an existing integration. */
export function updateIntegration(
  id: string,
  input: IntegrationUpdateInput,
): Promise<Integration> {
  return patch<Integration>(integrationPath(id), input);
}

/** Delete an integration and its delivery history. */
export function deleteIntegration(id: string): Promise<void> {
  return del<void>(integrationPath(id));
}

/** Return the delivery ledger with optional filters. */
export function fetchDeliveries(
  filters: {
    status?: DeliveryStatus | null;
    integrationId?: string | null;
    limit?: number | null;
  } = {},
): Promise<Delivery[]> {
  const query = buildQuery({
    status: filters.status ?? undefined,
    integration_id: filters.integrationId ?? undefined,
    limit: filters.limit ?? undefined,
  });
  return get<Delivery[]>(`${BASE}/deliveries${query}`);
}

/** Queue a delivery for another attempt. */
export function retryDelivery(id: string): Promise<Delivery> {
  return post<Delivery>(`${BASE}/deliveries/${encodeURIComponent(id)}/retry`);
}

/** Record a simulated transport result for a delivery. */
export function simulateDelivery(
  id: string,
  input: SimulationInput,
): Promise<Delivery> {
  return post<Delivery>(
    `${BASE}/deliveries/${encodeURIComponent(id)}/simulate`,
    input,
  );
}

/** Dispatch an event to matching integrations. */
export function dispatchEvent(input: DispatchInput): Promise<Delivery[]> {
  return post<Delivery[]>(`${BASE}/dispatch`, input);
}

/** Return every event adapter. */
export function fetchAdapters(): Promise<Adapter[]> {
  return get<Adapter[]>(`${BASE}/adapters`);
}

/** Register an event adapter. */
export function createAdapter(input: AdapterCreateInput): Promise<Adapter> {
  return post<Adapter>(`${BASE}/adapters`, input);
}

/** Delete an event adapter. */
export function deleteAdapter(id: string): Promise<void> {
  return del<void>(`${BASE}/adapters/${encodeURIComponent(id)}`);
}

/** Return the aggregated integration statistics. */
export function fetchStats(): Promise<IntegrationStats> {
  return get<IntegrationStats>(`${BASE}/stats`);
}

/** The adapter grouped for callers that prefer a single import. */
export const integrationsApi = {
  fetchIntegrations,
  fetchIntegration,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  fetchDeliveries,
  retryDelivery,
  simulateDelivery,
  dispatchEvent,
  fetchAdapters,
  createAdapter,
  deleteAdapter,
  fetchStats,
};

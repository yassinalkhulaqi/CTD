/**
 * Low level HTTP client used by every data fetching hook.
 */

import type { ErrorEnvelope } from "./types";

/** Error thrown when the API responds with a non 2xx status. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    message: string,
    status: number,
    code = "unknown_error",
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Return whether the failure was caused by missing credentials. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** Return whether the failure was caused by insufficient permissions. */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** Return whether the resource could not be found. */
  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** Return whether the caller exceeded the request budget. */
  get isRateLimited(): boolean {
    return this.status === 429;
  }
}

/** Options accepted by the request helpers. */
export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON body serialised before transmission. */
  json?: unknown;
  /** Optional abort signal used to cancel in-flight requests. */
  signal?: AbortSignal;
}

const BASE_URL = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "";

/**
 * Build a query string from a record of parameters.
 *
 * @param params - The parameters to serialise.
 * @returns The encoded query string, including the leading `?` when needed.
 */
export function buildQuery(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

/**
 * Parse a response body, tolerating empty and non JSON payloads.
 *
 * @param response - The fetch response to read.
 * @returns The parsed payload or `null`.
 */
async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (response.status === 204) return null;
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    return text ? text : null;
  }
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
}

/**
 * Perform an HTTP request against the dashboard API.
 *
 * @param path - The API path, relative to the API base URL.
 * @param options - Request options.
 * @returns The parsed response body.
 * @throws {ApiError} When the server responds with an error status.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, headers, signal, ...rest } = options;
  const finalHeaders = new Headers(headers);
  if (json !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
  }
  finalHeaders.set("Accept", "application/json");

  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    signal,
    headers: finalHeaders,
    body: json === undefined ? undefined : JSON.stringify(json),
  });

  const payload = await parseBody(response);

  if (!response.ok) {
    const envelope = payload as ErrorEnvelope | null;
    const error = envelope?.error;
    throw new ApiError(
      error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      error?.code ?? "unknown_error",
      error?.details ?? {},
    );
  }

  return payload as T;
}

/**
 * Perform a GET request.
 *
 * @param path - The API path.
 * @param options - Request options.
 * @returns The parsed response body.
 */
export function get<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: "GET" });
}

/**
 * Perform a POST request.
 *
 * @param path - The API path.
 * @param json - The JSON body.
 * @param options - Request options.
 * @returns The parsed response body.
 */
export function post<T>(path: string, json?: unknown, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: "POST", json });
}

/**
 * Perform a PATCH request.
 *
 * @param path - The API path.
 * @param json - The JSON body.
 * @param options - Request options.
 * @returns The parsed response body.
 */
export function patch<T>(path: string, json?: unknown, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: "PATCH", json });
}

/**
 * Perform a PUT request.
 *
 * @param path - The API path.
 * @param json - The JSON body.
 * @param options - Request options.
 * @returns The parsed response body.
 */
export function put<T>(path: string, json?: unknown, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: "PUT", json });
}

/**
 * Perform a DELETE request.
 *
 * @param path - The API path.
 * @param options - Request options.
 * @returns The parsed response body.
 */
export function del<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: "DELETE" });
}

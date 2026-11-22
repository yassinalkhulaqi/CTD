/**
 * The HTTP client used by every data fetching hook.
 *
 * The client adds the authentication header, deduplicates identical in-flight
 * requests, retries transient failures with exponential backoff and normalises
 * every failure into an {@link ApiError}.
 */

import type { ErrorEnvelope } from "../types";

/** Error thrown when the API responds with a non 2xx status. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly retryAfter: number | null;

  constructor(
    message: string,
    status: number,
    code = "unknown_error",
    details: Record<string, unknown> = {},
    retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfter = retryAfter;
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

  /** Return whether the failure is worth retrying. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status === 408 || this.status >= 500;
  }
}

/** Options accepted by the request helpers. */
export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON body serialised before transmission. */
  json?: unknown;
  /** Optional abort signal used to cancel in-flight requests. */
  signal?: AbortSignal;
  /** Number of retries for transient failures. */
  retries?: number;
  /** Base delay of the exponential backoff, in milliseconds. */
  retryDelay?: number;
  /** Override the request timeout, in milliseconds. */
  timeout?: number;
  /** Skip the deduplication of identical in-flight requests. */
  dedupe?: boolean;
}

/** The base URL of the dashboard API. */
export const API_BASE_URL =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined)?.replace(
    /\/$/,
    "",
  ) ?? "";

/** Resolves the bearer token used for authenticated requests. */
export type TokenResolver = () => string | null;

/** Resolves a refresh token used to renew an expired session. */
export type RefreshResolver = () => Promise<boolean>;

let tokenResolver: TokenResolver = () => null;
let refreshResolver: RefreshResolver = async () => false;

/**
 * Register the resolvers used to attach credentials and refresh sessions.
 *
 * @param resolveToken - Resolves the current access token.
 * @param refresh - Attempts to refresh an expired session.
 */
export function configureAuth(
  resolveToken: TokenResolver,
  refresh?: RefreshResolver,
): void {
  tokenResolver = resolveToken;
  if (refresh) refreshResolver = refresh;
}

/**
 * Build a query string from a record of parameters.
 *
 * @param params - The parameters to serialise.
 * @returns The encoded query string, including the leading `?` when needed.
 */
export function buildQuery(
  params?: Record<string, string | number | boolean | null | undefined>,
): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
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
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") ?? "";
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
 * Convert an unknown failure into an {@link ApiError}.
 *
 * @param error - The raw failure.
 * @returns The normalised error.
 */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof DOMException && error.name === "AbortError") {
    return new ApiError("The request was cancelled", 0, "aborted");
  }
  if (error instanceof TypeError) {
    return new ApiError("The server could not be reached", 0, "network_error");
  }
  const message = error instanceof Error ? error.message : "Unexpected error";
  return new ApiError(message, 0, "unknown_error");
}

const inFlight = new Map<string, Promise<unknown>>();

/**
 * Sleep for the given duration.
 *
 * @param ms - The duration in milliseconds.
 * @returns A promise resolved after the delay.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/**
 * Perform a single HTTP request without retries or deduplication.
 *
 * @param path - The API path.
 * @param method - The HTTP method.
 * @param options - Request options.
 * @returns The parsed response body.
 * @throws {ApiError} When the server responds with an error status.
 */
async function performRequest<T>(
  path: string,
  method: string,
  options: RequestOptions,
): Promise<T> {
  const { json, headers, signal, timeout = 30_000, ...rest } = options;

  const finalHeaders = new Headers(headers);
  if (json !== undefined) finalHeaders.set("Content-Type", "application/json");
  finalHeaders.set("Accept", "application/json");

  const token = tokenResolver();
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const controller = new AbortController();
  const abortFromCaller = () => controller.abort();
  signal?.addEventListener("abort", abortFromCaller);

  const timer = setTimeout(() => controller.abort(), timeout);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      method,
      headers: finalHeaders,
      signal: controller.signal,
      body: json === undefined ? undefined : JSON.stringify(json),
    });
  } catch (error) {
    if (signal?.aborted)
      throw new ApiError("The request was cancelled", 0, "aborted");
    throw toApiError(error);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abortFromCaller);
  }

  const payload = await parseBody(response);

  if (!response.ok) {
    const envelope = payload as ErrorEnvelope | null;
    const error = envelope?.error;
    const retryHeader = response.headers.get("retry-after");
    throw new ApiError(
      error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      error?.code ?? "unknown_error",
      error?.details ?? {},
      retryHeader ? Number(retryHeader) : null,
    );
  }

  return payload as T;
}

/**
 * Perform an HTTP request against the dashboard API.
 *
 * @param path - The API path, relative to the API base URL.
 * @param options - Request options.
 * @returns The parsed response body.
 * @throws {ApiError} When the server responds with an error status.
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const retries = options.retries ?? (method === "GET" ? 2 : 0);
  const retryDelay = options.retryDelay ?? 300;

  const dedupe = options.dedupe ?? method === "GET";
  const key = `${method} ${path} ${JSON.stringify(options.json ?? null)}`;

  const execute = async (): Promise<T> => {
    let attempt = 0;
    for (;;) {
      try {
        return await performRequest<T>(path, method, options);
      } catch (error) {
        const apiError = toApiError(error);
        const canRetry =
          attempt < retries &&
          apiError.isRetryable &&
          apiError.code !== "aborted";

        if (!canRetry) {
          if (apiError.isUnauthorized && (await refreshResolver())) {
            attempt += 1;
            continue;
          }
          throw apiError;
        }

        const backoff = retryDelay * 2 ** attempt;
        const jitter = Math.random() * retryDelay * 0.4;
        await sleep(backoff + jitter);
        attempt += 1;
      }
    }
  };

  if (!dedupe) return execute();

  const existing = inFlight.get(key);
  if (existing) return existing as Promise<T>;

  const promise = execute().finally(() => {
    inFlight.delete(key);
  });
  inFlight.set(key, promise);
  return promise;
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
export function post<T>(
  path: string,
  json?: unknown,
  options: RequestOptions = {},
): Promise<T> {
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
export function patch<T>(
  path: string,
  json?: unknown,
  options: RequestOptions = {},
): Promise<T> {
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
export function put<T>(
  path: string,
  json?: unknown,
  options: RequestOptions = {},
): Promise<T> {
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

/**
 * Return the number of requests currently in flight.
 *
 * @returns The size of the deduplication map.
 */
export function pendingRequestCount(): number {
  return inFlight.size;
}

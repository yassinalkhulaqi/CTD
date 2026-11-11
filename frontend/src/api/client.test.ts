import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, buildQuery, configureAuth, get, request, toApiError } from "./client";

const originalFetch = globalThis.fetch;

function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const spy = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(String(input), init)),
  );
  globalThis.fetch = spy as unknown as typeof fetch;
  return spy;
}

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

describe("buildQuery", () => {
  it("encodes the parameters", () => {
    expect(buildQuery({ a: 1, b: "x" })).toBe("?a=1&b=x");
  });

  it("skips empty values", () => {
    expect(buildQuery({ a: undefined, b: null, c: "" })).toBe("");
  });

  it("returns an empty string without parameters", () => {
    expect(buildQuery()).toBe("");
  });
});

describe("request", () => {
  beforeEach(() => {
    configureAuth(() => null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns the parsed body", async () => {
    mockFetch(() => jsonResponse({ id: "team-1" }));
    await expect(request<{ id: string }>("/api/teams/team-1")).resolves.toEqual({
      id: "team-1",
    });
  });

  it("throws an ApiError carrying the error envelope", async () => {
    mockFetch(() =>
      jsonResponse({ error: { code: "not_found", message: "missing" } }, 404),
    );
    await expect(get("/api/teams/nope")).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      message: "missing",
    });
  });

  it("attaches the bearer token when one is available", async () => {
    configureAuth(() => "token-123");
    const spy = mockFetch(() => jsonResponse({}));
    await get("/api/teams");
    const init = spy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("deduplicates identical in-flight GET requests", async () => {
    const spy = mockFetch(() => jsonResponse({ ok: true }));
    await Promise.all([get("/api/teams"), get("/api/teams")]);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("retries transient server errors", async () => {
    let attempts = 0;
    mockFetch(() => {
      attempts += 1;
      if (attempts < 3) return jsonResponse({ error: { message: "boom" } }, 500);
      return jsonResponse({ ok: true });
    });
    await expect(get("/api/teams", { retryDelay: 1 })).resolves.toEqual({ ok: true });
    expect(attempts).toBe(3);
  });

  it("does not retry client errors", async () => {
    let attempts = 0;
    mockFetch(() => {
      attempts += 1;
      return jsonResponse({ error: { message: "nope" } }, 400);
    });
    await expect(get("/api/teams")).rejects.toBeInstanceOf(ApiError);
    expect(attempts).toBe(1);
  });

  it("sends the JSON body of a mutation", async () => {
    const spy = mockFetch(() => jsonResponse({ id: "team-2" }, 201));
    await request("/api/teams", { method: "POST", json: { name: "Team" } });
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "Team" }));
  });
});

describe("toApiError", () => {
  it("passes ApiError instances through", () => {
    const error = new ApiError("boom", 500);
    expect(toApiError(error)).toBe(error);
  });

  it("maps network failures", () => {
    const error = toApiError(new TypeError("Failed to fetch"));
    expect(error.code).toBe("network_error");
    expect(error.status).toBe(0);
  });

  it("marks server errors as retryable", () => {
    expect(new ApiError("boom", 503).isRetryable).toBe(true);
    expect(new ApiError("boom", 400).isRetryable).toBe(false);
  });
});

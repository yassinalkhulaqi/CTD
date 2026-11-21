import { beforeEach, describe, expect, it, vi } from "vitest";
import { del, get, patch, post } from "../../api/client";
import * as api from "./api";

vi.mock("../../api/client", () => ({
  buildQuery: (
    params?: Record<string, string | number | boolean | null | undefined>,
  ): string => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value === undefined || value === null || value === "") continue;
      search.set(key, String(value));
    }
    const encoded = search.toString();
    return encoded ? `?${encoded}` : "";
  },
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(get).mockReset();
  vi.mocked(post).mockReset();
  vi.mocked(patch).mockReset();
  vi.mocked(del).mockReset();
});

describe("integration endpoints", () => {
  it("lists and fetches integrations", async () => {
    vi.mocked(get).mockResolvedValueOnce([]);
    await api.fetchIntegrations();
    expect(get).toHaveBeenCalledWith("/api/integrations");

    vi.mocked(get).mockResolvedValueOnce({ id: "int-1" });
    await api.fetchIntegration("int 1");
    expect(get).toHaveBeenCalledWith("/api/integrations/int%201");
  });

  it("creates and updates integrations with typed payloads", async () => {
    const input = {
      name: "Alerts",
      kind: "webhook" as const,
      endpoint_url: "https://example.com/hook",
      events: ["challenge.solved"],
      secret: "secret-value",
      enabled: true,
    };
    vi.mocked(post).mockResolvedValueOnce({ id: "int-1" });
    await api.createIntegration(input);
    expect(post).toHaveBeenCalledWith("/api/integrations", input);

    vi.mocked(patch).mockResolvedValueOnce({ id: "int-1" });
    await api.updateIntegration("int-1", { enabled: false });
    expect(patch).toHaveBeenCalledWith("/api/integrations/int-1", {
      enabled: false,
    });
  });

  it("deletes an integration", async () => {
    vi.mocked(del).mockResolvedValueOnce(undefined);
    await api.deleteIntegration("int-1");
    expect(del).toHaveBeenCalledWith("/api/integrations/int-1");
  });
});

describe("delivery endpoints", () => {
  it("builds filtered delivery queries", async () => {
    vi.mocked(get).mockResolvedValueOnce([]);
    await api.fetchDeliveries({
      status: "failed",
      integrationId: "int-1",
      limit: 10,
    });
    expect(get).toHaveBeenCalledWith(
      "/api/integrations/deliveries?status=failed&integration_id=int-1&limit=10",
    );
  });

  it("retries, simulates and dispatches deliveries", async () => {
    vi.mocked(post).mockResolvedValueOnce({ id: "del-1" });
    await api.retryDelivery("del-1");
    expect(post).toHaveBeenCalledWith(
      "/api/integrations/deliveries/del-1/retry",
    );

    vi.mocked(post).mockResolvedValueOnce({ id: "del-1" });
    await api.simulateDelivery("del-1", {
      status: "failed",
      response_code: 503,
    });
    expect(post).toHaveBeenCalledWith(
      "/api/integrations/deliveries/del-1/simulate",
      {
        status: "failed",
        response_code: 503,
      },
    );

    vi.mocked(post).mockResolvedValueOnce([]);
    await api.dispatchEvent({
      event: "challenge.solved",
      payload: { points: 100 },
    });
    expect(post).toHaveBeenCalledWith("/api/integrations/dispatch", {
      event: "challenge.solved",
      payload: { points: 100 },
    });
  });

  it("propagates failures from the client", async () => {
    vi.mocked(get).mockRejectedValueOnce(new Error("offline"));
    await expect(api.fetchDeliveries()).rejects.toThrow("offline");
  });
});

describe("adapter and stats endpoints", () => {
  it("lists, creates and deletes adapters", async () => {
    vi.mocked(get).mockResolvedValueOnce([]);
    await api.fetchAdapters();
    expect(get).toHaveBeenCalledWith("/api/integrations/adapters");

    vi.mocked(post).mockResolvedValueOnce({ id: "adt-1" });
    await api.createAdapter({
      name: "Bridge",
      event_map: { "challenge.solved": "score.changed" },
    });
    expect(post).toHaveBeenCalledWith("/api/integrations/adapters", {
      name: "Bridge",
      event_map: { "challenge.solved": "score.changed" },
    });

    vi.mocked(del).mockResolvedValueOnce(undefined);
    await api.deleteAdapter("adt-1");
    expect(del).toHaveBeenCalledWith("/api/integrations/adapters/adt-1");
  });

  it("reads the statistics endpoint", async () => {
    vi.mocked(get).mockResolvedValueOnce({ total_deliveries: 0 });
    await api.fetchStats();
    expect(get).toHaveBeenCalledWith("/api/integrations/stats");
  });
});

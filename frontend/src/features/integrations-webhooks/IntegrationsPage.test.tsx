import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as api from "./api";
import IntegrationsPage from "./IntegrationsPage";
import type { Adapter, Delivery, Integration, IntegrationStats } from "./types";

vi.mock("./api", () => ({
  fetchIntegrations: vi.fn(),
  fetchIntegration: vi.fn(),
  createIntegration: vi.fn(),
  updateIntegration: vi.fn(),
  deleteIntegration: vi.fn(),
  fetchDeliveries: vi.fn(),
  retryDelivery: vi.fn(),
  simulateDelivery: vi.fn(),
  dispatchEvent: vi.fn(),
  fetchAdapters: vi.fn(),
  createAdapter: vi.fn(),
  deleteAdapter: vi.fn(),
  fetchStats: vi.fn(),
}));

const integration: Integration = {
  id: "int-1",
  name: "Primary hooks",
  kind: "webhook",
  endpoint_url: "https://example.com/hook",
  events: ["challenge.solved"],
  masked_secret: "whsec_1234abcd••••efgh",
  has_secret: true,
  enabled: true,
  created_at: "2026-01-02T03:04:05Z",
  host: "example.com",
  scheme: "https",
  event_count: 1,
  is_active: true,
  subscribers_label: "challenge.solved",
};

const delivery: Delivery = {
  id: "del-1",
  integration_id: "int-1",
  event: "challenge.solved",
  payload: { data: { flag: "CTF{ok}" } },
  status: "pending",
  attempts: 0,
  response_code: null,
  sent_at: null,
  signature: "",
  can_retry: true,
  retry_after_seconds: 2,
  status_label: "Pending",
};

const adapter: Adapter = {
  id: "adt-1",
  name: "Bridge",
  event_map: { "challenge.solved": "score.changed" },
  mapping_count: 1,
  created_at: "2026-01-02T03:04:05Z",
};

const stats: IntegrationStats = {
  total_integrations: 1,
  enabled_integrations: 1,
  total_adapters: 1,
  total_deliveries: 1,
  pending_deliveries: 1,
  successful_deliveries: 0,
  failed_deliveries: 0,
  success_rate: 0,
  failure_rate: 0,
  average_attempts: 0,
  last_sent_at: null,
  by_event: { "challenge.solved": 1 },
  by_kind: { webhook: 1 },
};

beforeEach(() => {
  vi.mocked(api.fetchIntegrations).mockResolvedValue([integration]);
  vi.mocked(api.fetchDeliveries).mockResolvedValue([delivery]);
  vi.mocked(api.fetchAdapters).mockResolvedValue([adapter]);
  vi.mocked(api.fetchStats).mockResolvedValue(stats);
  vi.mocked(api.createIntegration).mockResolvedValue(integration);
  vi.mocked(api.updateIntegration).mockResolvedValue({
    ...integration,
    enabled: false,
  });
  vi.mocked(api.deleteIntegration).mockResolvedValue(undefined);
  vi.mocked(api.dispatchEvent).mockResolvedValue([delivery]);
  vi.mocked(api.retryDelivery).mockResolvedValue(delivery);
  vi.mocked(api.simulateDelivery).mockResolvedValue(delivery);
  vi.mocked(api.createAdapter).mockResolvedValue(adapter);
  vi.mocked(api.deleteAdapter).mockResolvedValue(undefined);
});

describe("IntegrationsPage", () => {
  it("loads integrations, adapters and statistics", async () => {
    render(<IntegrationsPage />);
    expect(
      await screen.findByRole("heading", { name: "Primary hooks" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Control plane")).toBeInTheDocument();
    expect(api.fetchIntegrations).toHaveBeenCalledTimes(1);
    expect(api.fetchStats).toHaveBeenCalledTimes(1);
  });

  it("toggles an integration and shows the result", async () => {
    render(<IntegrationsPage />);
    const toggle = await screen.findByRole("switch", {
      name: "Enable Primary hooks",
    });
    fireEvent.click(toggle);
    await waitFor(() =>
      expect(api.updateIntegration).toHaveBeenCalledWith("int-1", {
        enabled: false,
      }),
    );
    expect(await screen.findByText("Primary hooks paused")).toBeInTheDocument();
  });

  it("validates and submits the create form", async () => {
    render(<IntegrationsPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: "New integration" }),
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Create integration" }));
    expect(screen.getByText("Give the integration a name")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "New hooks" },
    });
    fireEvent.change(screen.getByLabelText("Endpoint URL"), {
      target: { value: "https://example.com/new" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create integration" }));
    await waitFor(() =>
      expect(api.createIntegration).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "New hooks",
          endpoint_url: "https://example.com/new",
          events: ["challenge.solved"],
        }),
      ),
    );
  });

  it("dispatches a test event from the deliveries view", async () => {
    render(<IntegrationsPage />);
    await screen.findByRole("heading", { name: "Primary hooks" });
    fireEvent.click(screen.getByRole("button", { name: "Deliveries" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Dispatch test event" }),
    );
    await waitFor(() =>
      expect(api.dispatchEvent).toHaveBeenCalledWith({
        event: "challenge.solved",
        payload: { challenge: "web-100" },
      }),
    );
    expect(
      await screen.findByText("Dispatched Challenge solved"),
    ).toBeInTheDocument();
  });

  it("surfaces load failures with a retry action", async () => {
    vi.mocked(api.fetchStats).mockRejectedValueOnce(
      new Error("backend unavailable"),
    );
    render(<IntegrationsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "backend unavailable",
    );
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
  });
});

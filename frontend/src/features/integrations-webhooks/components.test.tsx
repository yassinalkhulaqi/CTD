import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  AdapterCard,
  DeliveryInspector,
  EventSelector,
  IntegrationCard,
  IntegrationStats,
  SecretField,
} from "./components";
import type {
  Adapter,
  Delivery,
  Integration,
  IntegrationStats as Stats,
} from "./types";

const integration: Integration = {
  id: "int-1",
  name: "Primary hooks",
  kind: "webhook",
  endpoint_url: "https://example.com/hook",
  events: ["challenge.solved", "score.changed"],
  masked_secret: "whsec_1234abcd••••efgh",
  has_secret: true,
  enabled: true,
  created_at: "2026-01-02T03:04:05Z",
  host: "example.com",
  scheme: "https",
  event_count: 2,
  is_active: true,
  subscribers_label: "challenge.solved, score.changed",
};

const delivery: Delivery = {
  id: "del-1",
  integration_id: "int-1",
  event: "challenge.solved",
  payload: { event: "challenge.solved", data: { flag: "CTF{ok}" } },
  status: "failed",
  attempts: 1,
  response_code: 503,
  sent_at: "2026-01-02T03:04:05Z",
  signature: "abc123",
  can_retry: true,
  retry_after_seconds: 4,
  status_label: "Failed",
};

const stats: Stats = {
  total_integrations: 1,
  enabled_integrations: 1,
  total_adapters: 1,
  total_deliveries: 1,
  pending_deliveries: 0,
  successful_deliveries: 0,
  failed_deliveries: 1,
  success_rate: 0,
  failure_rate: 1,
  average_attempts: 1,
  last_sent_at: null,
  by_event: { "challenge.solved": 1 },
  by_kind: { webhook: 1 },
};

describe("IntegrationCard", () => {
  it("renders the endpoint, events and secret hints", () => {
    render(
      <IntegrationCard
        integration={integration}
        onToggle={() => undefined}
        onEdit={() => undefined}
        onDelete={() => undefined}
        onSendTest={() => undefined}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Primary hooks" }),
    ).toBeInTheDocument();
    expect(screen.getByText("https://example.com/hook")).toBeInTheDocument();
    expect(screen.getByText("Challenge solved")).toBeInTheDocument();
    expect(screen.getByText(/one-way digest/)).toBeInTheDocument();
  });

  it("reports enable toggles and actions", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    render(
      <IntegrationCard
        integration={integration}
        onToggle={onToggle}
        onEdit={() => undefined}
        onDelete={onDelete}
        onSendTest={() => undefined}
      />,
    );
    fireEvent.click(
      screen.getByRole("switch", { name: "Enable Primary hooks" }),
    );
    expect(onToggle).toHaveBeenCalledWith(false);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});

describe("SecretField", () => {
  it("toggles input visibility and aria state", () => {
    render(<SecretField value="supersecret" configured />);
    const input = screen.getByLabelText("Signing secret") as HTMLInputElement;
    expect(input.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: "Reveal secret" }));
    expect(input.type).toBe("text");
    expect(screen.getByRole("button", { name: "Hide secret" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("reports changes without exposing plaintext in hints", () => {
    const onChange = vi.fn();
    render(
      <SecretField value="" onChange={onChange} hint="Stored as a digest" />,
    );
    fireEvent.change(screen.getByLabelText("Signing secret"), {
      target: { value: "another-secret" },
    });
    expect(onChange).toHaveBeenCalledWith("another-secret");
    expect(screen.queryByText("another-secret")).not.toBeInTheDocument();
  });
});

describe("EventSelector", () => {
  it("adds and removes events", () => {
    const onChange = vi.fn();
    render(
      <EventSelector selected={["challenge.solved"]} onChange={onChange} />,
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /Score changed/ }));
    expect(onChange).toHaveBeenCalledWith([
      "challenge.solved",
      "score.changed",
    ]);

    onChange.mockClear();
    fireEvent.click(screen.getByRole("checkbox", { name: /Challenge solved/ }));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("shows validation errors and respects disabled state", () => {
    render(
      <EventSelector
        selected={[]}
        onChange={() => undefined}
        error="Pick one"
        disabled
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Pick one");
    expect(screen.getAllByRole("checkbox")[0]).toBeDisabled();
  });
});

describe("DeliveryInspector", () => {
  it("shows an empty state when there are no deliveries", () => {
    render(
      <DeliveryInspector
        deliveries={[]}
        integrations={[]}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByText("No deliveries yet")).toBeInTheDocument();
  });

  it("inspects payloads and retries failed deliveries", () => {
    const onRetry = vi.fn();
    const onSimulate = vi.fn();
    render(
      <DeliveryInspector
        deliveries={[delivery]}
        integrations={[integration]}
        onRetry={onRetry}
        onSimulate={onSimulate}
      />,
    );
    expect(screen.getByText("Primary hooks")).toBeInTheDocument();
    expect(screen.getByText("HTTP 503")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Challenge solved/ }));
    expect(screen.getByText(/CTF\{ok\}/)).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Retry delivery del-1" }),
    );
    expect(onRetry).toHaveBeenCalledWith("del-1");
    fireEvent.click(screen.getByRole("button", { name: "Success" }));
    expect(onSimulate).toHaveBeenCalledWith("del-1", "success");
  });

  it("disables retry for successful deliveries", () => {
    render(
      <DeliveryInspector
        deliveries={[
          {
            ...delivery,
            status: "success",
            can_retry: false,
            response_code: 200,
          },
        ]}
        integrations={[]}
        onRetry={() => undefined}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Retry delivery del-1" }),
    ).toBeDisabled();
  });
});

describe("AdapterCard", () => {
  it("renders mappings and delete action", () => {
    const onDelete = vi.fn();
    const adapter: Adapter = {
      id: "adt-1",
      name: "Bridge",
      event_map: { "challenge.solved": "score.changed" },
      mapping_count: 1,
      created_at: "2026-01-02T03:04:05Z",
    };
    render(<AdapterCard adapter={adapter} onDelete={onDelete} />);
    expect(screen.getByRole("heading", { name: "Bridge" })).toBeInTheDocument();
    expect(screen.getByText("Challenge solved")).toBeInTheDocument();
    expect(screen.getByText("Score changed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Delete adapter" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});

describe("IntegrationStats", () => {
  it("renders totals, outcomes and busiest events", () => {
    render(<IntegrationStats stats={stats} />);
    expect(screen.getByText("Integrations")).toBeInTheDocument();
    expect(screen.getByText("Busiest events")).toBeInTheDocument();
    expect(screen.getByText("Challenge solved · 1")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "0",
    );
  });

  it("handles missing statistics", () => {
    render(<IntegrationStats stats={null} />);
    expect(screen.getByText("Statistics are unavailable.")).toBeInTheDocument();
  });
});

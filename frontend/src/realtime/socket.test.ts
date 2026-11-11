import { beforeEach, describe, expect, it, vi } from "vitest";
import { RealtimeClient, buildSocketUrl } from "./socket";

class FakeSocket {
  static instances: FakeSocket[] = [];
  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  open() {
    this.readyState = 1;
    this.onopen?.();
  }

  emit(frame: unknown) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }
}

describe("buildSocketUrl", () => {
  it("builds a websocket url", () => {
    expect(buildSocketUrl("http://localhost:8000")).toBe("ws://localhost:8000/ws");
  });

  it("uses the secure protocol for https hosts", () => {
    expect(buildSocketUrl("https://dashboard.example")).toBe("wss://dashboard.example/ws");
  });

  it("appends the team filter", () => {
    expect(buildSocketUrl("http://localhost:8000", "team-1")).toContain("team_id=team-1");
  });

  it("appends the resume cursor", () => {
    expect(buildSocketUrl("http://localhost:8000", null, 42)).toContain("last_event_id=42");
  });
});

describe("RealtimeClient", () => {
  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket as unknown as typeof WebSocket);
  });

  it("connects and reports the open state", () => {
    const states: string[] = [];
    const client = new RealtimeClient({ onStateChange: (state) => states.push(state) });
    client.connect();

    expect(FakeSocket.instances).toHaveLength(1);
    FakeSocket.instances[0].open();
    expect(states).toContain("connecting");
    expect(states).toContain("open");
  });

  it("forwards the received events", () => {
    const events: unknown[] = [];
    const client = new RealtimeClient({ onEvent: (event) => events.push(event) });
    client.connect();
    FakeSocket.instances[0].open();
    FakeSocket.instances[0].emit({
      v: 1,
      type: "event",
      id: null,
      ts: "2026-01-01T00:00:00Z",
      payload: {
        id: 12,
        team_id: "team-1",
        kind: "solve.created",
        payload: {},
        occurred_at: "2026-01-01T00:00:00Z",
      },
    });

    expect(events).toHaveLength(1);
    expect((events[0] as { kind: string }).kind).toBe("solve.created");
  });

  it("stores the subscriber identifier sent by the server", () => {
    const client = new RealtimeClient();
    client.connect();
    FakeSocket.instances[0].open();
    FakeSocket.instances[0].emit({
      v: 1,
      type: "hello",
      id: null,
      ts: "2026-01-01T00:00:00Z",
      payload: { subscriber_id: "ws-42" },
    });

    expect(client.getState().subscriberId).toBe("ws-42");
  });

  it("sends a subscribe frame", () => {
    const client = new RealtimeClient();
    client.connect();
    FakeSocket.instances[0].open();
    client.subscribe("team-1", ["solve.created"]);

    const sent = FakeSocket.instances[0].sent.map((raw) => JSON.parse(raw) as { type: string });
    expect(sent[0].type).toBe("subscribe");
  });

  it("reports the malformed frames", () => {
    const errors: Error[] = [];
    const client = new RealtimeClient({ onError: (error) => errors.push(error) });
    client.connect();
    FakeSocket.instances[0].open();
    FakeSocket.instances[0].onmessage?.({ data: "not json" });

    expect(errors).toHaveLength(1);
  });

  it("stops reconnecting once it is closed", () => {
    const states: string[] = [];
    const client = new RealtimeClient({
      onStateChange: (state) => states.push(state),
      reconnectDelay: 5,
    });
    client.connect();
    client.close();
    expect(states).toContain("closed");
  });
});

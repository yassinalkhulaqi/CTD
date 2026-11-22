/**
 * A resilient websocket client for the realtime dashboard channel.
 *
 * The client reconnects with an exponential backoff, replays the events
 * missed during a disconnection and exposes the connection state to the UI.
 */

import { getAccessToken } from "../features/auth/tokenStorage";

/** The lifecycle of the realtime connection. */
export type ConnectionState =
  "idle" | "connecting" | "open" | "reconnecting" | "closed";

/** The frames exchanged with the server. */
export type ServerFrameType =
  "hello" | "event" | "snapshot" | "ping" | "pong" | "error" | "bye";

/** A frame received from the server. */
export interface ServerFrame {
  v: number;
  type: ServerFrameType;
  id: string | null;
  ts: string;
  payload: Record<string, unknown>;
}

/** The payload of an event frame. */
export interface EventPayload {
  id: number;
  team_id: string | null;
  kind: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

/** Options accepted by the {@link RealtimeClient}. */
export interface RealtimeClientOptions {
  /** The base URL of the API. */
  baseUrl?: string;
  /** The team the stream is restricted to. */
  teamId?: string | null;
  /** The delay before the first reconnection attempt, in milliseconds. */
  reconnectDelay?: number;
  /** The maximum delay between two reconnection attempts, in milliseconds. */
  maxReconnectDelay?: number;
  /** Called for every event received from the server. */
  onEvent?: (event: EventPayload) => void;
  /** Called whenever the connection state changes. */
  onStateChange?: (state: ConnectionState) => void;
  /** Called when the server reports an error. */
  onError?: (error: Error) => void;
}

/** The current state of the realtime client. */
export interface RealtimeClientState {
  /** The lifecycle of the connection. */
  state: ConnectionState;
  /** The number of reconnection attempts since the last successful open. */
  attempts: number;
  /** The identifier assigned by the server. */
  subscriberId: string | null;
}

/**
 * Build the websocket URL of the realtime channel.
 *
 * @param baseUrl - The base URL of the API.
 * @param teamId - Optional team filter.
 * @param lastEventId - Optional event identifier used to resume a stream.
 * @returns The absolute websocket URL.
 */
export function buildSocketUrl(
  baseUrl = "",
  teamId?: string | null,
  lastEventId?: number | null,
): string {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "http://localhost";
  const base = baseUrl || origin;
  const protocol = base.startsWith("https") ? "wss" : "ws";
  const host = base.replace(/^https?:\/\//, "").replace(/\/$/, "");
  const params = new URLSearchParams();
  if (teamId) params.set("team_id", teamId);
  if (lastEventId !== undefined && lastEventId !== null) {
    params.set("last_event_id", String(lastEventId));
  }
  const query = params.toString();
  return `${protocol}://${host}/ws${query ? `?${query}` : ""}`;
}

/**
 * A reconnecting websocket client.
 */
export class RealtimeClient {
  private socket: WebSocket | null = null;
  private readonly options: RealtimeClientOptions;
  private reconnectTimer: number | null = null;
  private pingTimer: number | null = null;
  private closed = false;
  private attempts = 0;
  private subscriberId: string | null = null;
  private lastEventId: number | null = null;
  private state: ConnectionState = "idle";

  constructor(options: RealtimeClientOptions = {}) {
    this.options = options;
  }

  /**
   * Return the current state of the client.
   *
   * @returns The state.
   */
  getState(): RealtimeClientState {
    return {
      state: this.state,
      attempts: this.attempts,
      subscriberId: this.subscriberId,
    };
  }

  /**
   * Open the connection.
   */
  connect(): void {
    this.closed = false;
    this.open();
  }

  /**
   * Close the connection and stop the reconnection attempts.
   */
  close(): void {
    this.closed = true;
    this.clearTimers();
    if (this.socket) {
      this.socket.close(1000, "client closed");
      this.socket = null;
    }
    this.setState("closed");
  }

  /**
   * Send a subscribe message narrowing the delivered events.
   *
   * @param teamId - Optional team filter.
   * @param kinds - Optional kind filter.
   */
  subscribe(teamId?: string | null, kinds?: string[]): void {
    this.send({
      type: "subscribe",
      payload: {
        team_id: teamId ?? null,
        kinds: kinds ?? [],
      },
    });
  }

  /**
   * Send a ping frame.
   */
  ping(): void {
    this.send({ type: "ping", payload: {} });
  }

  private open(): void {
    if (this.closed) return;
    this.setState(this.attempts === 0 ? "connecting" : "reconnecting");

    const url = buildSocketUrl(
      this.options.baseUrl,
      this.options.teamId,
      this.lastEventId,
    );
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      this.attempts = 0;
      this.setState("open");
      this.startPing();
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      this.handleFrame(event.data);
    };

    socket.onerror = () => {
      this.options.onError?.(new Error("The realtime connection failed"));
    };

    socket.onclose = () => {
      this.stopPing();
      this.socket = null;
      if (this.closed) return;
      this.setState("reconnecting");
      this.scheduleReconnect();
    };
  }

  private handleFrame(raw: string): void {
    let frame: ServerFrame;
    try {
      frame = JSON.parse(raw) as ServerFrame;
    } catch {
      this.options.onError?.(new Error("Received a malformed realtime frame"));
      return;
    }

    if (frame.type === "hello") {
      this.subscriberId = (frame.payload.subscriber_id as string) ?? null;
      return;
    }

    if (frame.type === "event") {
      const event = frame.payload as unknown as EventPayload;
      if (typeof event?.id === "number") {
        this.lastEventId = event.id;
      }
      if (event && typeof event === "object" && "kind" in event) {
        this.options.onEvent?.(event);
      }
    }
  }

  private send(frame: {
    type: string;
    payload: Record<string, unknown>;
  }): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify(frame));
  }

  private scheduleReconnect(): void {
    this.attempts += 1;
    const base = this.options.reconnectDelay ?? 1000;
    const max = this.options.maxReconnectDelay ?? 15_000;
    const delay = Math.min(max, base * 2 ** (this.attempts - 1));
    const jitter = Math.random() * base * 0.3;
    this.reconnectTimer = window.setTimeout(() => this.open(), delay + jitter);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = window.setInterval(() => this.ping(), 25_000);
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      window.clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private clearTimers(): void {
    this.stopPing();
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private setState(state: ConnectionState): void {
    if (this.state === state) return;
    this.state = state;
    this.options.onStateChange?.(state);
  }
}

/**
 * Build the authorisation headers of the websocket handshake.
 *
 * @returns The headers, empty when the dashboard runs in open mode.
 */
export function socketAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
